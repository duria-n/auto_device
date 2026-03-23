"""config.py — 应用全局配置"""
from __future__ import annotations
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes")


class Config:
    # ── Flask 基础 ────────────────────────────────────────────────────
    DEBUG   = _bool("FLASK_DEBUG", False)
    TESTING = False
    HOST    = os.getenv("HOST", "0.0.0.0")
    PORT    = int(os.getenv("PORT", "5000"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 MB

    # ── 访问控制 ──────────────────────────────────────────────────────
    # 是否启用访问码（局域网多用户场景下建议开启）
    ENABLE_ACCESS_CODE  = _bool("ENABLE_ACCESS_CODE", False)
    # 访问码：空时自动随机生成，写入 .env 后固定
    ACCESS_CODE         = os.getenv("ACCESS_CODE", "") or secrets.token_urlsafe(8)
    # 会话有效期（秒），默认 8 小时
    SESSION_LIFETIME    = int(os.getenv("SESSION_LIFETIME", str(8 * 3600)))
    SECRET_KEY          = os.getenv("SECRET_KEY", secrets.token_hex(32))

    # ── 并发限制 ──────────────────────────────────────────────────────
    # 同时处理的最大生成任务数（LLM 模式下防止并发爆显存）
    MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))

    # ── OLED 领域默认参数 ─────────────────────────────────────────────
    DEFAULT_SUBSTRATE = "玻璃基板"
    DEFAULT_ANODE     = "ITO"
    DEFAULT_ANODE_THK = 150
    DEFAULT_CATHODE   = "Al"
    TADF_THRESHOLD    = 0.3

    ROLE_LABELS: dict[str, str] = {
        "hil":        "HIL 空穴注入层",
        "htl":        "HTL 空穴传输层",
        "ebl":        "EBL 电子阻挡层",
        "host":       "EML 主体材料",
        "sensitizer": "EML 敏化剂",
        "emitter":    "EML 发光体",
        "hbl":        "HBL 空穴阻挡层",
        "etl":        "ETL 电子传输层",
        "eil":        "EIL 电子注入层",
    }
    ROLE_ORDER: list[str] = [
        "hil", "htl", "ebl", "host", "sensitizer", "emitter", "hbl", "etl", "eil"
    ]

    # ── LLM API Keys ──────────────────────────────────────────────────
    LLM_PROVIDER    = os.getenv("LLM_PROVIDER",   "openai")
    LLM_MODEL       = os.getenv("LLM_MODEL",       "gpt-4o")
    LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY",    "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    QWEN_API_KEY      = os.getenv("QWEN_API_KEY",      "")
    DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY",  "")

    # ── HuggingFace 本地推理 ──────────────────────────────────────────
    HF_TOKEN       = os.getenv("HF_TOKEN",      "")
    HF_CACHE_DIR   = os.getenv("HF_CACHE_DIR",  "")
    HF_DEVICE      = os.getenv("HF_DEVICE",     "auto")
    HF_TORCH_DTYPE = os.getenv("HF_TORCH_DTYPE","auto")

    HF_RECOMMENDED_MODELS: list[dict] = [
        {"id": "Qwen/Qwen2.5-7B-Instruct",               "desc": "7B · 中文强 · 推荐首选"},
        {"id": "Qwen/Qwen2.5-14B-Instruct",              "desc": "14B · 效果更好 · 需更多显存"},
        {"id": "Qwen/Qwen2.5-32B-Instruct",              "desc": "32B · 旗舰 · 需 A100 级"},
        {"id": "THUDM/chatglm3-6b",                       "desc": "6B · 清华 GLM · 中文强"},
        {"id": "THUDM/glm-4-9b-chat",                    "desc": "9B · GLM-4 · 最新版"},
        {"id": "meta-llama/Llama-3.1-8B-Instruct",       "desc": "8B · 需 HF Token"},
        {"id": "mistralai/Mistral-7B-Instruct-v0.3",     "desc": "7B · 英文强"},
        {"id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B","desc": "7B · 推理蒸馏版"},
    ]

    PROVIDER_MODELS: dict[str, list[str]] = {
        "openai":      ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "anthropic":   ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5-20251001"],
        "qwen":        ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"],
        "deepseek":    ["deepseek-chat", "deepseek-reasoner"],
        "huggingface": [],
    }
