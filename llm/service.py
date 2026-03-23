"""llm/service.py — LLM 服务层，三种模式统一入口"""
from __future__ import annotations
from core.models import DeviceRecipe
from core.template_engine import generate_text
from core.constants import DEFAULT_SECTIONS, TADF_THRESHOLD
from .base import LLMConfig
from .providers import get_provider
from .prompt_builder import build_system_prompt, build_polish_prompt, build_direct_prompt


def generate_template_only(recipe: DeviceRecipe, sections: list[str]) -> str:
    """模式A：纯模板引擎，不调用任何 LLM。"""
    return generate_text(recipe, sections)


def generate_with_template_polish(
    recipe: DeviceRecipe,
    sections: list[str],
    llm_cfg: LLMConfig,
) -> str:
    """模式B：模板引擎生成草稿 → LLM 润色。"""
    draft    = generate_text(recipe, sections)
    system   = build_system_prompt()
    user     = build_polish_prompt(draft, recipe.device_no, sections)
    provider = get_provider(llm_cfg)
    result   = provider.chat(system, user)
    return result or draft   # LLM 失败时回退草稿


def generate_with_llm_direct(
    recipe: DeviceRecipe,
    sections: list[str],
    llm_cfg: LLMConfig,
) -> str:
    """模式C：LLM 根据结构化数据直接撰写全文。"""
    system   = build_system_prompt()
    user     = build_direct_prompt(recipe, sections)
    provider = get_provider(llm_cfg)
    return provider.chat(system, user)


def generate(
    recipe: DeviceRecipe,
    sections: list[str] | None = None,
    llm_cfg: LLMConfig | None = None,
    mode: str = "template",
) -> str:
    """
    统一生成入口。

    Parameters
    ----------
    mode : str
        "template"        — 纯模板（无需 llm_cfg）
        "template_polish" — 模板草稿 + LLM 润色
        "llm_direct"      — LLM 直写
    """
    secs = sections or DEFAULT_SECTIONS
    if llm_cfg is None or mode == "template":
        return generate_template_only(recipe, secs)
    if mode == "template_polish":
        return generate_with_template_polish(recipe, secs, llm_cfg)
    if mode == "llm_direct":
        return generate_with_llm_direct(recipe, secs, llm_cfg)
    raise ValueError(f"未知 mode: {mode!r}，可选: template / template_polish / llm_direct")
