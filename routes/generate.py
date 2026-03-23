"""routes/generate.py — 器件例生成相关 API 路由"""
from __future__ import annotations
import io
from flask import Blueprint, request, jsonify, send_file, current_app
import pandas as pd

from core.models import DeviceRecipe, MaterialLayer
from core.parser import parse_row, parse_dataframe
from core.constants import DEFAULT_SECTIONS
from llm.base import LLMConfig
from llm.service import generate

bp = Blueprint("generate", __name__)


def _llm_cfg_from_request(body: dict) -> LLMConfig | None:
    llm = body.get("llm", {})
    provider = llm.get("provider", "").strip().lower()
    if not provider:
        return None

    cfg = LLMConfig(
        provider    = provider,
        model       = llm.get("model", ""),
        api_key     = llm.get("api_key", "").strip(),
        max_tokens  = int(llm.get("max_tokens", 2048)),
        temperature = float(llm.get("temperature", 0.3)),
    )

    if provider == "huggingface":
        cfg.hf_cache_dir      = llm.get("hf_cache_dir",      "")
        cfg.hf_device         = llm.get("hf_device",         "auto")
        cfg.hf_torch_dtype    = llm.get("hf_torch_dtype",    "auto")
        cfg.hf_load_in_4bit   = bool(llm.get("hf_load_in_4bit",  False))
        cfg.hf_load_in_8bit   = bool(llm.get("hf_load_in_8bit",  False))
        cfg.hf_token          = llm.get("hf_token",          "")
        cfg.hf_max_new_tokens = int(llm.get("hf_max_new_tokens", 2048))
        if not cfg.model:
            return None
    elif not cfg.api_key:
        return None

    return cfg


def _recipe_from_body(body: dict) -> DeviceRecipe:
    data = body.get("data", {})
    mats = [MaterialLayer.from_dict(m) for m in data.get("materials", [])]
    return DeviceRecipe(
        device_no   = data.get("device_no", "实施例1"),
        substrate   = data.get("substrate", "玻璃基板"),
        anode       = data.get("anode", "ITO"),
        anode_thk   = data.get("anode_thk", ""),
        cathode     = data.get("cathode", "Al"),
        cathode_thk = data.get("cathode_thk", ""),
        homo        = data.get("homo", ""),
        lumo        = data.get("lumo", ""),
        s1          = data.get("s1", ""),
        t1          = data.get("t1", ""),
        f           = data.get("f", ""),
        dipole      = data.get("dipole", ""),
        lambda_hole = data.get("lambda_hole", ""),
        lambda_elec = data.get("lambda_elec", ""),
        von         = data.get("von", ""),
        vop         = data.get("vop", ""),
        vth         = data.get("vth", ""),
        eqe         = data.get("eqe", ""),
        cda         = data.get("cda", ""),
        ciex        = data.get("ciex", ""),
        ciey        = data.get("ciey", ""),
        el_peak     = data.get("el_peak", ""),
        t95         = data.get("t95", ""),
        lmax        = data.get("lmax", ""),
        materials   = mats,
    )


# ── 单条生成 ──────────────────────────────────────────────────────────
@bp.route("/api/generate", methods=["POST"])
def api_generate():
    sem = getattr(current_app, "job_semaphore", None)
    acquired = sem.acquire(blocking=False) if sem else True
    if not acquired:
        return jsonify({
            "success": False,
            "error": f"服务器繁忙，当前并发任务已满，请稍后重试"
        }), 503
    try:
        body     = request.get_json(force=True)
        sections = body.get("sections", DEFAULT_SECTIONS)
        mode     = body.get("mode", "template")
        recipe   = _recipe_from_body(body)
        llm_cfg  = _llm_cfg_from_request(body)
        text     = generate(recipe, sections, llm_cfg, mode)
        return jsonify({"success": True, "text": text, "mode": mode})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if sem and acquired:
            sem.release()


# ── CSV 批量生成 ───────────────────────────────────────────────────────
@bp.route("/api/batch", methods=["POST"])
def api_batch():
    sem = getattr(current_app, "job_semaphore", None)
    acquired = sem.acquire(blocking=False) if sem else True
    if not acquired:
        return jsonify({
            "success": False,
            "error": "服务器繁忙，请稍后重试"
        }), 503
    try:
        sections_str = request.form.get("sections", "")
        sections     = sections_str.split(",") if sections_str else DEFAULT_SECTIONS
        mode         = request.form.get("mode", "template")

        llm_cfg = None
        api_key = request.form.get("api_key", "").strip()
        if api_key:
            llm_cfg = LLMConfig(
                provider    = request.form.get("provider", "openai"),
                model       = request.form.get("model", "gpt-4o"),
                api_key     = api_key,
                max_tokens  = int(request.form.get("max_tokens", 2048)),
                temperature = float(request.form.get("temperature", 0.3)),
            )

        file = request.files.get("file")
        if not file:
            return jsonify({"success": False, "error": "未上传文件"}), 400

        fname = file.filename.lower()
        df = pd.read_excel(file) if fname.endswith((".xlsx", ".xls")) \
            else pd.read_csv(file, encoding="utf-8-sig")

        recipes = parse_dataframe(df)
        results = []
        for i, recipe in enumerate(recipes):
            text = generate(recipe, sections, llm_cfg, mode)
            results.append({
                "index":     i + 1,
                "device_no": recipe.device_no,
                "text":      text,
            })

        return jsonify({"success": True, "results": results, "total": len(results)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if sem and acquired:
            sem.release()


# ── 导出 TXT ──────────────────────────────────────────────────────────
@bp.route("/api/export_txt", methods=["POST"])
def api_export_txt():
    try:
        body  = request.get_json(force=True)
        texts = body.get("texts", [])
        combined = ("\n\n" + "=" * 60 + "\n\n").join(texts)
        buf = io.BytesIO(combined.encode("utf-8"))
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name="器件例专利文本.txt",
                         mimetype="text/plain; charset=utf-8")
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _make_csv_header(n_bp: int) -> str:
    """生成 n_bp 个功能层的 CSV 表头字符串。"""
    base = "device_no,substrate,anode,anode_thk,cathode,cathode_thk"
    bp_fields = ",".join(
        f"BP{i}_name,BP{i}_role,BP{i}THK,"
        f"BP{i}_HOMO,BP{i}_LUMO,BP{i}_S1,BP{i}_T1,"
        f"BP{i}_f,BP{i}_Dipole,BP{i}_Lambda_hole,BP{i}_Lambda_electron,BP{i}_ratio"
        for i in range(1, n_bp + 1)
    )
    perf = "Von,Vop,Vth,EQE,CdA,CIEx,CIEy,EL_peak,T95,Lmax"
    return f"{base},{bp_fields},{perf}\n"


def _make_csv_example_row(n_bp: int) -> str:
    """生成一行示例数据（仅前几层有值，其余留空）。"""
    defaults = {
        1: ("HATCN",  "hil",        "10",  "-9.6","-5.5","","","","","","",""),
        2: ("NPB",    "htl",        "40",  "-5.4","-2.4","","","","","","",""),
        3: ("MADN",   "host",       "30",  "-5.9","-2.7","","","","","","","97"),
        4: ("DSA-ph", "emitter",    "",    "-5.4","-2.5","2.90","2.62","0.92","3.1","0.15","0.18","3"),
        5: ("Liq",    "etl",        "30",  "-2.0","-0.8","","","","","","",""),
    }
    row = "实施例1,玻璃基板,ITO,150,Al,"
    for i in range(1, n_bp + 1):
        if i in defaults:
            row += ",".join(defaults[i]) + ","
        else:
            row += ",,,,,,,,,,," + ","   # 空列
    row = row.rstrip(",")
    row += ",,,,,,,,,,"   # 性能列
    return row + "\n"


# ── 下载 CSV 模板（支持指定层数）────────────────────────────────────
@bp.route("/api/sample_csv")
def api_sample_csv():
    """下载 CSV 模板，默认 5 层，可通过 ?n=N 指定层数。"""
    try:
        n = int(request.args.get("n", 5))
        n = max(1, min(n, 30))   # 限制 1~30 层
    except (ValueError, TypeError):
        n = 5

    header  = _make_csv_header(n)
    example = _make_csv_example_row(n)
    content = header + example

    buf = io.BytesIO(content.encode("utf-8-sig"))
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"OLED器件例模板_{n}层.csv",
                     mimetype="text/csv; charset=utf-8-sig")
