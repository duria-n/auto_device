"""config.py — 应用全局配置"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Config:
    DEBUG   = True
    HOST    = "0.0.0.0"
    PORT    = 5000
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    DEFAULT_SUBSTRATE = "玻璃基板"
    DEFAULT_ANODE     = "ITO"
    DEFAULT_ANODE_THK = 150
    DEFAULT_CATHODE   = "Al"
    TADF_THRESHOLD    = 0.3

    ROLE_LABELS: dict[str, str] = {
        "hil":     "HIL 空穴注入层",
        "htl":     "HTL 空穴传输层",
        "ebl":     "EBL 电子阻挡层",
        "host":    "EML 主体材料",
        "emitter": "EML 发光体",
        "hbl":     "HBL 空穴阻挡层",
        "etl":     "ETL 电子传输层",
        "eil":     "EIL 电子注入层",
    }
    ROLE_ORDER: list[str] = [
        "hil", "htl", "ebl", "host", "emitter", "hbl", "etl", "eil"
    ]

    # LLM 默认（从 .env 读取）
    LLM_PROVIDER    = os.getenv("LLM_PROVIDER",    "openai")
    LLM_MODEL       = os.getenv("LLM_MODEL",        "gpt-4o")
    LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY",   "")
    ANTHROPIC_API_KEY= os.getenv("ANTHROPIC_API_KEY","")
    QWEN_API_KEY     = os.getenv("QWEN_API_KEY",     "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

    # ── HuggingFace 本地推理配置 ─────────────────────────────────────
    HF_TOKEN      = os.getenv("HF_TOKEN", "")               # HF Access Token（私有/门控模型）
    HF_CACHE_DIR  = os.getenv("HF_CACHE_DIR", "")           # 权重缓存目录，空则用 HF 默认
    HF_DEVICE     = os.getenv("HF_DEVICE",    "auto")       # auto | cpu | cuda | cuda:0 | mps
    HF_TORCH_DTYPE= os.getenv("HF_TORCH_DTYPE","auto")      # auto | float16 | bfloat16

    # 推荐模型列表（中文专利场景优先）
    HF_RECOMMENDED_MODELS: list[dict] = [
        {"id": "Qwen/Qwen2.5-7B-Instruct",          "desc": "7B · 中文强 · 推荐首选"},
        {"id": "Qwen/Qwen2.5-14B-Instruct",         "desc": "14B · 效果更好 · 需更多显存"},
        {"id": "Qwen/Qwen2.5-32B-Instruct",         "desc": "32B · 旗舰 · 需 A100 级"},
        {"id": "THUDM/chatglm3-6b",                  "desc": "6B · 清华 GLM · 中文强"},
        {"id": "THUDM/glm-4-9b-chat",               "desc": "9B · GLM-4 · 最新版"},
        {"id": "meta-llama/Llama-3.1-8B-Instruct",  "desc": "8B · 需 HF Token"},
        {"id": "mistralai/Mistral-7B-Instruct-v0.3","desc": "7B · 英文强"},
        {"id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B","desc": "7B · 推理蒸馏版"},
    ]

    # 供前端下拉（API 模型）
    PROVIDER_MODELS: dict[str, list[str]] = {
        "openai":       ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "anthropic":    ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5-20251001"],
        "qwen":         ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"],
        "deepseek":     ["deepseek-chat", "deepseek-reasoner"],
        "huggingface":  [],   # 由用户自行输入 model_id
    }
