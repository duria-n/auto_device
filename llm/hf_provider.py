"""
llm/hf_provider.py — HuggingFace 本地推理 Provider

流程：
  1. 首次调用时从 HF Hub 下载模型权重到 hf_cache_dir（或默认缓存）
  2. 将 pipeline 缓存在进程内（_PIPELINE_CACHE），后续复用，无需重复加载
  3. 支持 4-bit / 8-bit 量化（需要 bitsandbytes）
  4. 支持 CPU / CUDA / MPS 设备

依赖（按需安装）：
  pip install transformers accelerate
  pip install bitsandbytes          # 量化支持（可选）
  pip install torch                 # 本地推理必须

推荐模型（中文专利场景）：
  Qwen/Qwen2.5-7B-Instruct          # 7B，中文强，推荐首选
  Qwen/Qwen2.5-14B-Instruct         # 14B，效果更好，需更多显存
  THUDM/chatglm3-6b                 # 清华 GLM，中文强
  meta-llama/Llama-3.1-8B-Instruct  # 需要 HF Token（门控模型）
  mistralai/Mistral-7B-Instruct-v0.3
"""
from __future__ import annotations
import logging
import os
from typing import Any

from .base import BaseLLMProvider, LLMConfig

logger = logging.getLogger(__name__)

# ── 进程级 Pipeline 缓存（避免重复加载权重）─────────────────────────
# key: (model_id, device, dtype, load_in_4bit, load_in_8bit, cache_dir)
_PIPELINE_CACHE: dict[tuple, Any] = {}
_LOAD_LOCK = __import__("threading").Lock()   # 防止并发下载同一模型损坏权重


def _make_cache_key(cfg: LLMConfig) -> tuple:
    return (
        cfg.model,
        cfg.hf_device,
        cfg.hf_torch_dtype,
        cfg.hf_load_in_4bit,
        cfg.hf_load_in_8bit,
        cfg.hf_cache_dir,
    )


def _load_pipeline(cfg: LLMConfig):
    """加载或复用 transformers pipeline（线程安全）。"""
    key = _make_cache_key(cfg)

    # 快速路径：已缓存直接返回（无锁检查，性能优先）
    if key in _PIPELINE_CACHE:
        logger.info(f"[HF] 复用已加载模型: {cfg.model}")
        return _PIPELINE_CACHE[key]

    # 加锁：防止多线程并发下载同一模型损坏权重文件
    with _LOAD_LOCK:
        # double-check：锁内再检查一次，避免等锁期间另一线程已完成加载
        if key in _PIPELINE_CACHE:
            return _PIPELINE_CACHE[key]

        try:
            import torch
            from transformers import (
                pipeline, BitsAndBytesConfig,
                AutoTokenizer, AutoModelForCausalLM,
            )
        except ImportError:
            raise ImportError(
                "本地 HuggingFace 推理需要安装:\n"
                "  pip install transformers accelerate torch\n"
                "  pip install bitsandbytes   # 量化支持（可选）"
            )

        # ── 加载新模型前：释放显存，防止 OOM ─────────────────────────
        if _PIPELINE_CACHE:
            logger.info(
                f"[HF] 已有 {len(_PIPELINE_CACHE)} 个模型在缓存中，"
                f"加载新模型 {cfg.model} 前先释放显存"
            )
            _release_vram(torch)

        model_id   = cfg.model
        cache_dir  = cfg.hf_cache_dir or None
        hf_token   = cfg.hf_token     or None

        # ── 设备选择 ──────────────────────────────────────────────────
        if cfg.hf_device == "auto":
            if torch.cuda.is_available():
                device_map = "auto"
                device     = None
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device_map = None
                device     = "mps"
            else:
                device_map = None
                device     = "cpu"
        else:
            device_map = None
            device     = cfg.hf_device

        # ── dtype ──────────────────────────────────────────────────────
        dtype_map = {
            "float16":  torch.float16,
            "bfloat16": torch.bfloat16,
            "float32":  torch.float32,
            "auto":     "auto",
        }
        torch_dtype = dtype_map.get(cfg.hf_torch_dtype, "auto")

        # ── 量化配置 ───────────────────────────────────────────────────
        quantization_config = None
        if cfg.hf_load_in_4bit or cfg.hf_load_in_8bit:
            try:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit = cfg.hf_load_in_4bit,
                    load_in_8bit = cfg.hf_load_in_8bit,
                    bnb_4bit_compute_dtype = torch.bfloat16 if cfg.hf_load_in_4bit else None,
                )
            except Exception as e:
                logger.warning(f"[HF] 量化配置失败，回退到全精度: {e}")

        logger.info(
            f"[HF] 首次加载: {model_id} | "
            f"cache={cache_dir or '默认'} | device={device or device_map} | "
            f"dtype={cfg.hf_torch_dtype} | "
            f"4bit={cfg.hf_load_in_4bit} 8bit={cfg.hf_load_in_8bit}"
        )

        # ── 设置缓存目录环境变量 ──────────────────────────────────────
        if cache_dir:
            os.environ.setdefault("HF_HOME",            cache_dir)
            os.environ.setdefault("TRANSFORMERS_CACHE",  cache_dir)
            os.environ.setdefault("HF_DATASETS_CACHE",   cache_dir)

        # ── 加载 tokenizer + model ────────────────────────────────────
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            cache_dir         = cache_dir,
            token             = hf_token,
            trust_remote_code = True,
        )

        model_kwargs: dict[str, Any] = {
            "cache_dir":          cache_dir,
            "token":              hf_token,
            "trust_remote_code":  True,
            "torch_dtype":        torch_dtype,
        }
        if device_map:
            model_kwargs["device_map"] = device_map
        if quantization_config:
            model_kwargs["quantization_config"] = quantization_config

        model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
        if device and not device_map:
            model = model.to(device)

        pipe = pipeline(
            "text-generation",
            model     = model,
            tokenizer = tokenizer,
            device    = device if not device_map else None,
        )

        _PIPELINE_CACHE[key] = pipe
        logger.info(f"[HF] 模型加载完成: {model_id}")
        return pipe


class HuggingFaceProvider(BaseLLMProvider):
    """
    HuggingFace 本地推理 Provider。

    首次调用自动下载权重；后续从进程缓存直接推理。
    支持 chat-template（models 带 apply_chat_template 的均可用）。
    """

    def chat(self, system: str, user: str) -> str:
        pipe = _load_pipeline(self.cfg)
        tokenizer = pipe.tokenizer

        # ── 构建消息列表 ──────────────────────────────────────────────
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]

        # 用 chat template 格式化（支持 Qwen/GLM/LLaMA 等）
        if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize        = False,
                add_generation_prompt = True,
            )
        else:
            # 回退：手动拼接
            prompt = f"System: {system}\n\nUser: {user}\n\nAssistant:"

        outputs = pipe(
            prompt,
            max_new_tokens  = self.cfg.hf_max_new_tokens,
            temperature     = self.cfg.temperature,
            do_sample       = self.cfg.temperature > 0,
            pad_token_id    = tokenizer.eos_token_id,
            return_full_text= False,   # 只返回生成部分，不含 prompt
        )

        return outputs[0]["generated_text"].strip()


def _release_vram(torch_module=None) -> None:
    """
    清空 pipeline 缓存并释放显存/内存。
    在加载新模型前或手动卸载时调用。
    """
    import gc
    # 先清缓存引用，让 Python GC 可以回收
    _PIPELINE_CACHE.clear()
    gc.collect()
    # 释放 CUDA 显存
    try:
        if torch_module is None:
            import torch as _torch
            torch_module = _torch
        if torch_module.cuda.is_available():
            torch_module.cuda.empty_cache()
            torch_module.cuda.synchronize()
            logger.info("[HF] CUDA 显存已释放")
    except Exception as e:
        logger.debug(f"[HF] 释放 CUDA 显存时跳过: {e}")


def get_model_info(model_id: str, hf_token: str = "") -> dict:
    """
    查询 HF Hub 上模型的基本信息（无需下载权重）。
    用于前端显示模型描述、参数量等。
    """
    try:
        from huggingface_hub import model_info
        info = model_info(model_id, token=hf_token or None)
        return {
            "id":          info.modelId,
            "downloads":   getattr(info, "downloads", None),
            "likes":       getattr(info, "likes",     None),
            "tags":        getattr(info, "tags",       []),
            "pipeline_tag":getattr(info, "pipeline_tag", ""),
        }
    except Exception as e:
        return {"error": str(e)}


def clear_pipeline_cache(model_id: str | None = None) -> None:
    """
    清除进程内 pipeline 缓存并释放显存/内存。
    model_id=None 时清除全部缓存。
    """
    with _LOAD_LOCK:
        if model_id is None:
            _release_vram()
            logger.info("[HF] 已清除所有 pipeline 缓存并释放显存")
        else:
            keys = [k for k in _PIPELINE_CACHE if k[0] == model_id]
            for k in keys:
                del _PIPELINE_CACHE[k]
            # 局部清理后也尝试释放显存
            import gc, torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"[HF] 已卸载 {model_id}（清除 {len(keys)} 个缓存条目）")
