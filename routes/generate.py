"""routes/generate.py — 器件例生成相关 API 路由"""
from __future__ import annotations
import io
from flask import Blueprint, request, jsonify, send_file
import pandas as pd

from core.models import DeviceRecipe, MaterialLayer
from core.parser import parse_row, parse_dataframe
from core.constants import DEFAULT_SECTIONS
from llm.base import LLMConfig
from llm.service import generate

bp = Blueprint("generate", __name__)


def _llm_cfg_from_request(body: dict) -> LLMConfig | None:
    """从请求体中提取 LLM 配置；若无 provider 或纯模板模式则返回 None。"""
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

    # HuggingFace 专用字段
    if provider == "huggingface":
        cfg.hf_cache_dir     = llm.get("hf_cache_dir",   "")
        cfg.hf_device        = llm.get("hf_device",      "auto")
        cfg.hf_torch_dtype   = llm.get("hf_torch_dtype", "auto")
        cfg.hf_load_in_4bit  = bool(llm.get("hf_load_in_4bit",  False))
        cfg.hf_load_in_8bit  = bool(llm.get("hf_load_in_8bit",  False))
        cfg.hf_token         = llm.get("hf_token", "")
        cfg.hf_max_new_tokens= int(llm.get("hf_max_new_tokens", 2048))
        # HF 不需要 api_key，但 model 字段就是 model_id
        if not cfg.model:
            return None

    elif not cfg.api_key:
        return None   # 非HF模式必须有 api_key

    return cfg


def _recipe_from_body(body: dict) -> DeviceRecipe:
    """将前端 JSON 转为 DeviceRecipe（手动输入模式）。"""
    data = body.get("data", {})
    mats = [MaterialLayer.from_dict(m) for m in data.get("materials", [])]
    recipe = DeviceRecipe(
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
    return recipe


# ── 单条生成 ──────────────────────────────────────────────────────────
@bp.route("/api/generate", methods=["POST"])
def api_generate():
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


# ── CSV 批量生成 ───────────────────────────────────────────────────────
@bp.route("/api/batch", methods=["POST"])
def api_batch():
    try:
        sections_str = request.form.get("sections", "")
        sections     = sections_str.split(",") if sections_str else DEFAULT_SECTIONS
        mode         = request.form.get("mode", "template")

        # LLM 配置从 form 字段读取
        llm_cfg = None
        api_key = request.form.get("api_key", "").strip()
        if api_key:
            llm_cfg = LLMConfig(
                provider    = request.form.get("provider", "openai"),
                model       = request.form.get("model", "gpt-4o"),
                api_key     = api_key,
                secret_key  = request.form.get("secret_key", ""),
                max_tokens  = int(request.form.get("max_tokens", 4096)),
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


# ── 下载 CSV 模板 ─────────────────────────────────────────────────────
@bp.route("/api/sample_csv")
def api_sample_csv():
    sample = (
        "device_no,substrate,anode,anode_thk,cathode,cathode_thk,"
        "BP1_name,BP1_role,BP1THK,BP1_HOMO,BP1_LUMO,BP1_S1,BP1_T1,"
        "BP1_f,BP1_Dipole,BP1_Lambda_hole,BP1_Lambda_electron,BP1_ratio,"
        "BP2_name,BP2_role,BP2THK,BP2_HOMO,BP2_LUMO,BP2_S1,BP2_T1,"
        "BP2_f,BP2_Dipole,BP2_Lambda_hole,BP2_Lambda_electron,BP2_ratio,"
        "BP3_name,BP3_role,BP3THK,BP3_HOMO,BP3_LUMO,BP3_S1,BP3_T1,"
        "BP3_f,BP3_Dipole,BP3_Lambda_hole,BP3_Lambda_electron,BP3_ratio,"
        "BP4_name,BP4_role,BP4THK,BP4_HOMO,BP4_LUMO,BP4_S1,BP4_T1,"
        "BP4_f,BP4_Dipole,BP4_Lambda_hole,BP4_Lambda_electron,BP4_ratio,"
        "Von,Vop,Vth,EQE,CdA,CIEx,CIEy,EL_peak,T95,Lmax\n"
        "实施例1,玻璃基板,ITO,150,Al,,HATCN,hil,10,-9.6,-5.5,,,,,,,,"
        "NPB,htl,40,-5.4,-2.4,,,,,,,,MADN,host,30,-5.9,-2.7,,,,,,,97,"
        "DSA-ph,emitter,,−5.4,-2.5,2.90,2.62,0.92,3.1,0.15,0.18,3,"
        ",,,,,,,,,,\n"
    )
    buf = io.BytesIO(sample.encode("utf-8-sig"))
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name="OLED器件例模板.csv",
                     mimetype="text/csv; charset=utf-8-sig")
