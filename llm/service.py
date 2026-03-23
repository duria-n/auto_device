"""llm/service.py — LLM 服务层，三种模式统一入口"""
from __future__ import annotations
from core.models import DeviceRecipe
from core.template_engine import generate_text
from core.constants import DEFAULT_SECTIONS, TADF_THRESHOLD
from .base import LLMConfig
from .providers import get_provider
from .prompt_builder import build_system_prompt, build_polish_prompt, build_direct_prompt


def generate_template_only(
    recipe: DeviceRecipe,
    sections: list[str],
    comparisons=None,
) -> str:
    """模式A：纯模板引擎，不调用 LLM。"""
    return generate_text(recipe, sections, comparisons)


def generate_with_template_polish(
    recipe: DeviceRecipe,
    sections: list[str],
    llm_cfg: LLMConfig,
    comparisons=None,
) -> str:
    """模式B：模板引擎生成草稿 → LLM 润色。"""
    draft    = generate_text(recipe, sections, comparisons)
    system   = build_system_prompt()
    user     = build_polish_prompt(draft, recipe.device_no, sections)
    provider = get_provider(llm_cfg)
    result   = provider.chat(system, user)
    return result or draft


def generate_with_llm_direct(
    recipe: DeviceRecipe,
    sections: list[str],
    llm_cfg: LLMConfig,
    comparisons=None,
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
    comparisons=None,
) -> str:
    """
    统一生成入口。

    Parameters
    ----------
    recipe      : 主实施例配方
    sections    : 要生成的段落，默认全部
    llm_cfg     : LLM 配置，None 时强制走 template 模式
    mode        : "template" | "template_polish" | "llm_direct"
    comparisons : 对比例列表 [(变体DeviceRecipe, 变更说明), ...]
                  由 ComparisonStrategy.xxx() 生成，None 时对比例全占位符
    """
    secs = sections or DEFAULT_SECTIONS
    if llm_cfg is None or mode == "template":
        return generate_template_only(recipe, secs, comparisons)
    if mode == "template_polish":
        return generate_with_template_polish(recipe, secs, llm_cfg, comparisons)
    if mode == "llm_direct":
        return generate_with_llm_direct(recipe, secs, llm_cfg, comparisons)
    raise ValueError(f"未知 mode: {mode!r}，可选: template / template_polish / llm_direct")
