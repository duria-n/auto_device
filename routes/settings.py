"""routes/settings.py — LLM 配置相关 API"""
from __future__ import annotations
from flask import Blueprint, request, jsonify
from config import Config

bp = Blueprint("settings", __name__)


@bp.route("/api/providers", methods=["GET"])
def api_providers():
    """返回支持的 provider 及其模型列表（供前端下拉框使用）。"""
    return jsonify({
        "providers": Config.PROVIDER_MODELS,
        "default_provider": Config.LLM_PROVIDER,
        "default_model":    Config.LLM_MODEL,
    })


@bp.route("/api/validate_key", methods=["POST"])
def api_validate_key():
    """简单验证 API Key 是否可用（发送最小测试请求）。"""
    try:
        body     = request.get_json(force=True)
        provider = body.get("provider", "openai").lower()
        api_key  = body.get("api_key", "").strip()
        model    = body.get("model", "")
        secret   = body.get("secret_key", "")

        if not api_key:
            return jsonify({"valid": False, "error": "API Key 不能为空"}), 400

        from llm.base import LLMConfig
        from llm.providers import get_provider

        cfg = LLMConfig(
            provider   = provider,
            model      = model or Config.PROVIDER_MODELS.get(provider, [""])[0],
            api_key    = api_key,
            secret_key = secret,
            max_tokens = 10,
        )
        p = get_provider(cfg)
        p.chat("You are a test assistant.", "Reply OK")
        return jsonify({"valid": True, "provider": provider, "model": cfg.model})

    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 200


@bp.route("/api/save_key", methods=["POST"])
def api_save_key():
    """
    将 API Key 写入 .env 文件。
    安全限制：仅允许来自 localhost / 127.0.0.1 的请求，防止远程滥用。
    """
    import re
    from pathlib import Path
    from flask import request as req

    # ── 仅允许本机访问 ────────────────────────────────────────────────
    remote = req.remote_addr or ""
    allowed = {"127.0.0.1", "::1", "localhost"}
    # 也接受 X-Forwarded-For 为空（直连）或明确是 127.0.0.1
    forwarded = req.headers.get("X-Forwarded-For", "").strip()
    if remote not in allowed and forwarded not in ("", "127.0.0.1"):
        return jsonify({
            "success": False,
            "error": "save_key 仅允许本机（localhost）调用，当前来源被拒绝"
        }), 403

    try:
        body     = request.get_json(force=True)
        provider = body.get("provider", "").lower()
        api_key  = body.get("api_key", "").strip()
        if not provider or not api_key:
            return jsonify({"success": False, "error": "provider 和 api_key 不能为空"}), 400

        key_map = {
            "openai":    "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "qwen":      "QWEN_API_KEY",
            "deepseek":  "DEEPSEEK_API_KEY",
            "huggingface": "HF_TOKEN",
        }
        env_key = key_map.get(provider)
        if not env_key:
            return jsonify({"success": False, "error": f"未知 provider: {provider}"}), 400

        env_path = Path(__file__).resolve().parent.parent / ".env"
        content  = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

        line    = f'{env_key}="{api_key}"'
        pattern = re.compile(rf'^{env_key}=.*$', re.MULTILINE)
        content = pattern.sub(line, content) if pattern.search(content) \
                  else content.rstrip("\n") + f"\n{line}\n"

        env_path.write_text(content, encoding="utf-8")
        return jsonify({"success": True, "key": env_key})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
