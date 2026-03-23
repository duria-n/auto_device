"""llm/providers.py — OpenAI / Anthropic / Qwen / Deepseek 四家实现"""
from __future__ import annotations
from .base import BaseLLMProvider, LLMConfig


# ── OpenAI ────────────────────────────────────────────────────────────
class OpenAIProvider(BaseLLMProvider):
    def chat(self, system: str, user: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self.cfg.api_key)
        resp = client.chat.completions.create(
            model=self.cfg.model,
            max_tokens=self.cfg.max_tokens,
            temperature=self.cfg.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


# ── Anthropic ─────────────────────────────────────────────────────────
class AnthropicProvider(BaseLLMProvider):
    def chat(self, system: str, user: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.cfg.api_key)
        resp = client.messages.create(
            model=self.cfg.model,
            max_tokens=self.cfg.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text if resp.content else ""


# ── Qwen（通义千问，dashscope SDK）────────────────────────────────────
class QwenProvider(BaseLLMProvider):
    def chat(self, system: str, user: str) -> str:
        try:
            import dashscope
            from dashscope import Generation
        except ImportError:
            raise ImportError("pip install dashscope")
        dashscope.api_key = self.cfg.api_key
        resp = Generation.call(
            model=self.cfg.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens=self.cfg.max_tokens,
            temperature=self.cfg.temperature,
            result_format="message",
        )
        if resp.status_code == 200:
            return resp.output.choices[0].message.content or ""
        raise RuntimeError(f"Qwen API error {resp.status_code}: {resp.message}")


# ── Deepseek（兼容 OpenAI SDK）────────────────────────────────────────
class DeepseekProvider(BaseLLMProvider):
    def chat(self, system: str, user: str) -> str:
        from openai import OpenAI
        client = OpenAI(
            api_key=self.cfg.api_key,
            base_url="https://api.deepseek.com/v1",
        )
        resp = client.chat.completions.create(
            model=self.cfg.model,
            max_tokens=self.cfg.max_tokens,
            temperature=self.cfg.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


# ── 工厂 ──────────────────────────────────────────────────────────────
_MAP: dict[str, type[BaseLLMProvider]] = {
    "openai":        OpenAIProvider,
    "anthropic":     AnthropicProvider,
    "qwen":          QwenProvider,
    "deepseek":      DeepseekProvider,
    "huggingface":   None,   # 延迟导入，避免无 torch 环境启动失败
}


def get_provider(cfg: LLMConfig) -> BaseLLMProvider:
    key = cfg.provider.lower()
    if key == "huggingface":
        from .hf_provider import HuggingFaceProvider
        return HuggingFaceProvider(cfg)
    cls = _MAP.get(key)
    if not cls:
        raise ValueError(f"未知 provider: {cfg.provider!r}，可选: {list(_MAP)}")
    return cls(cfg)
