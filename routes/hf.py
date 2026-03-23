"""routes/hf.py — HuggingFace 本地模型管理路由"""
from __future__ import annotations
from flask import Blueprint, request, jsonify
from config import Config

bp = Blueprint("hf", __name__)


@bp.route("/api/hf/recommended", methods=["GET"])
def api_hf_recommended():
    """返回推荐模型列表。"""
    return jsonify({
        "models":    Config.HF_RECOMMENDED_MODELS,
        "cache_dir": Config.HF_CACHE_DIR or "~/.cache/huggingface",
        "device":    Config.HF_DEVICE,
    })


@bp.route("/api/hf/model_info", methods=["POST"])
def api_hf_model_info():
    """查询 HF Hub 模型信息（无需下载权重）。"""
    try:
        body     = request.get_json(force=True)
        model_id = body.get("model_id", "").strip()
        hf_token = body.get("hf_token", Config.HF_TOKEN)
        if not model_id:
            return jsonify({"success": False, "error": "model_id 不能为空"}), 400
        from llm.hf_provider import get_model_info
        info = get_model_info(model_id, hf_token)
        return jsonify({"success": True, "info": info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/hf/load", methods=["POST"])
def api_hf_load():
    """
    预加载模型权重（触发下载）。
    首次调用可能耗时较长，前端应显示进度提示。
    """
    try:
        body      = request.get_json(force=True)
        model_id  = body.get("model_id", "").strip()
        cache_dir = body.get("cache_dir", Config.HF_CACHE_DIR) or ""
        device    = body.get("device",    Config.HF_DEVICE)
        dtype     = body.get("dtype",     Config.HF_TORCH_DTYPE)
        load_4bit = bool(body.get("load_in_4bit", False))
        load_8bit = bool(body.get("load_in_8bit", False))
        hf_token  = body.get("hf_token",  Config.HF_TOKEN)

        if not model_id:
            return jsonify({"success": False, "error": "model_id 不能为空"}), 400

        from llm.base import LLMConfig
        from llm.hf_provider import _load_pipeline

        cfg = LLMConfig(
            provider       = "huggingface",
            model          = model_id,
            hf_cache_dir   = cache_dir,
            hf_device      = device,
            hf_torch_dtype = dtype,
            hf_load_in_4bit= load_4bit,
            hf_load_in_8bit= load_8bit,
            hf_token       = hf_token,
        )
        _load_pipeline(cfg)   # 触发下载 + 缓存
        return jsonify({"success": True, "model_id": model_id, "message": "模型已加载完成"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/hf/cache_status", methods=["POST"])
def api_hf_cache_status():
    """检查指定模型是否已在本地缓存（不触发下载）。"""
    try:
        body      = request.get_json(force=True)
        model_id  = body.get("model_id", "").strip()
        cache_dir = body.get("cache_dir", Config.HF_CACHE_DIR) or None

        try:
            from transformers.utils import cached_file
            from transformers import AutoConfig
            AutoConfig.from_pretrained(
                model_id,
                cache_dir      = cache_dir,
                local_files_only = True,   # 只查本地，不下载
                trust_remote_code = True,
            )
            cached = True
        except Exception:
            cached = False

        return jsonify({"success": True, "model_id": model_id, "cached": cached})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/hf/unload", methods=["POST"])
def api_hf_unload():
    """从进程缓存中卸载模型，释放显存/内存。"""
    try:
        body     = request.get_json(force=True)
        model_id = body.get("model_id", None)
        from llm.hf_provider import clear_pipeline_cache
        clear_pipeline_cache(model_id)
        msg = f"已卸载 {model_id}" if model_id else "已卸载所有模型"
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
