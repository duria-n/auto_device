"""llm/base.py — LLM Provider 抽象基类"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    provider:    str   = "openai"
    model:       str   = "gpt-4o"
    api_key:     str   = ""
    max_tokens:  int   = 2048
    temperature: float = 0.3
    secret_key:  str   = ""   # ERNIE 用

    # ── HuggingFace 本地推理专用字段 ─────────────────────────────────
    # model_id  : HF Hub 上的模型 ID，如 "Qwen/Qwen2.5-7B-Instruct"
    #             provider="huggingface" 时 model 字段也存此值
    hf_cache_dir:  str  = ""      # 权重缓存目录，空则用 HF 默认 (~/.cache/huggingface)
    hf_device:     str  = "auto"  # "auto" | "cpu" | "cuda" | "cuda:0" | "mps"
    hf_load_in_4bit:  bool = False  # bitsandbytes 4-bit 量化
    hf_load_in_8bit:  bool = False  # bitsandbytes 8-bit 量化
    hf_token:      str  = ""      # HF Access Token（私有模型/需登录的门控模型）
    hf_max_new_tokens: int = 2048  # 生成 token 数上限（对应 max_tokens）
    hf_torch_dtype: str = "auto"  # "auto" | "float16" | "bfloat16" | "float32"


class BaseLLMProvider(ABC):
    """所有 LLM Provider 实现此接口"""

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    @abstractmethod
    def chat(self, system: str, user: str) -> str:
        """发送 chat 请求，返回纯文本响应"""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
