"""llm/prompt_builder.py — 使用 Jinja2 渲染 .j2 prompt 模板"""
from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from core.models import DeviceRecipe
from core.constants import DEFAULT_SECTIONS, TADF_THRESHOLD

_PROMPT_DIR = Path(__file__).parent / "prompts"

_env = Environment(
    loader        = FileSystemLoader(str(_PROMPT_DIR)),
    undefined     = StrictUndefined,
    trim_blocks   = True,
    lstrip_blocks = True,
    keep_trailing_newline = True,
)
_env.filters["abs"] = abs


def _render(template_name: str, **ctx) -> str:
    return _env.get_template(template_name).render(**ctx).strip()


def build_system_prompt(tadf_threshold: float = TADF_THRESHOLD) -> str:
    """渲染 system.j2"""
    return _render("system.j2", tadf_threshold=tadf_threshold)


def build_polish_prompt(draft: str, device_no: str, sections: list[str]) -> str:
    """渲染 polish.j2（模板草稿润色模式）"""
    return _render("polish.j2", draft=draft, device_no=device_no, sections=sections)


def build_direct_prompt(
    recipe: DeviceRecipe,
    sections: list[str],
    tadf_threshold: float = TADF_THRESHOLD,
) -> str:
    """渲染 direct.j2（LLM直写模式）"""
    return _render("direct.j2", recipe=recipe, sections=sections, tadf_threshold=tadf_threshold)


if __name__ == "__main__":
    from core.models import DeviceRecipe, MaterialLayer

    demo = DeviceRecipe(
        device_no="实施例1", substrate="玻璃基板",
        anode="ITO", anode_thk="150", cathode="Al", cathode_thk="",
        homo="-5.42", lumo="-2.18", s1="2.85", t1="2.62",
        f="0.92", dipole="3.1", lambda_hole="0.15", lambda_elec="0.18",
        von="", vop="", eqe="", cda="", ciex="", ciey="0.35",
        el_peak="", t95="", lmax="",
        materials=[
            MaterialLayer(id="BP1", name="HATCN",  role="hil",    thk="10"),
            MaterialLayer(id="BP2", name="NPB",    role="htl",    thk="40", homo="-5.4", lumo="-2.4"),
            MaterialLayer(id="BP3", name="MADN",   role="host",   thk="30", homo="-5.9", lumo="-2.7", ratio="97"),
            MaterialLayer(id="BP4", name="DSA-ph", role="emitter", thk="",
                          homo="-5.4", lumo="-2.5", s1="2.90", t1="2.62",
                          f="0.92", dipole="3.1", lambda_hole="0.15", lambda_elec="0.18", ratio="3"),
            MaterialLayer(id="BP5", name="Liq",    role="etl",    thk="30"),
        ],
    )

    secs = ["structure", "material", "performance", "mechanism"]
    sep  = "=" * 70

    print(f"\n{sep}\n[system.j2]\n{sep}\n")
    print(build_system_prompt())

    print(f"\n{sep}\n[direct.j2]\n{sep}\n")
    print(build_direct_prompt(demo, secs))

    print(f"\n{sep}\n[polish.j2]\n{sep}\n")
    draft = "实施例1\n\n① 器件叠层结构描述\n\n（草稿…）\n\n④ 器件性能\n\n【待补充:EQE/%】"
    print(build_polish_prompt(draft, "实施例1", secs))
