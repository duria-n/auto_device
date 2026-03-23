"""core/parser.py — 将 CSV 行 / dict 解析为 DeviceRecipe"""
from __future__ import annotations
import re
from typing import Any
import pandas as pd
from .models import DeviceRecipe, MaterialLayer
from .constants import ROLE_ORDER


def _clean(v: Any) -> str:
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "") else s


def _get(row: dict, *keys: str) -> str:
    for k in keys:
        v = _clean(row.get(k, ""))
        if v:
            return v
    return ""


def parse_row(row: dict[str, Any], row_idx: int = 0) -> DeviceRecipe:
    """将 CSV 一行 dict 解析为 DeviceRecipe。"""
    recipe = DeviceRecipe(
        device_no   = _get(row, "device_no")   or f"实施例{row_idx + 1}",
        substrate   = _get(row, "substrate")   or "玻璃基板",
        anode       = _get(row, "anode")       or "ITO",
        anode_thk   = _get(row, "anode_thk", "ITO_THK"),
        cathode     = _get(row, "cathode")     or "Al",
        cathode_thk = _get(row, "cathode_thk", "Al_THK"),
        von         = _get(row, "Von",  "von"),
        vop         = _get(row, "Vop",  "vop"),
        vth         = _get(row, "Vth",  "vth"),
        eqe         = _get(row, "EQE",  "eqe"),
        cda         = _get(row, "CdA",  "cd/A", "CE", "C.E"),
        ciex        = _get(row, "CIEx", "ciex"),
        ciey        = _get(row, "CIEy", "ciey"),
        el_peak     = _get(row, "EL_peak", "el_peak"),
        t95         = _get(row, "T95",  "T95(H)"),
        lmax        = _get(row, "Lmax", "lmax"),
    )

    # 找出所有 BPn 前缀（通过 BPnTHK 列）
    bp_re = re.compile(r'^(BP\d+)THK$', re.IGNORECASE)
    bp_ids = sorted(
        {m.group(1).upper() for col in row if (m := bp_re.match(col))},
        key=lambda x: int(re.sub(r'\D', '', x))
    )

    for bp in bp_ids:
        mat = MaterialLayer(
            id           = bp,
            name         = _get(row, f"{bp}_name", bp),
            role         = _get(row, f"{bp}_role") or "htl",
            thk          = _get(row, f"{bp}THK"),
            ratio        = _get(row, f"{bp}_ratio"),
            smiles       = _get(row, f"{bp}_SMILES", f"{bp}_smiles"),
            homo         = _get(row, f"{bp}_HOMO",   f"{bp}_homo"),
            lumo         = _get(row, f"{bp}_LUMO",   f"{bp}_lumo"),
            s1           = _get(row, f"{bp}_S1",     f"{bp}_s1"),
            t1           = _get(row, f"{bp}_T1",     f"{bp}_t1"),
            f            = _get(row, f"{bp}_f",      f"{bp}_F"),
            dipole       = _get(row, f"{bp}_Dipole", f"{bp}_dipole"),
            lambda_hole  = _get(row, f"{bp}_Lambda_hole",     f"{bp}_lambda_hole"),
            lambda_elec  = _get(row, f"{bp}_Lambda_electron", f"{bp}_lambda_electron"),
        )
        recipe.materials.append(mat)

    # 按层序排列
    def _role_idx(m: MaterialLayer) -> int:
        try:
            return ROLE_ORDER.index(m.role)
        except ValueError:
            return 99

    recipe.materials.sort(key=_role_idx)

    # 将第一个 emitter 的量化参数提升到顶层（供 LLM prompt 使用）
    emitters = recipe.get_emitters()
    if emitters:
        e = emitters[0]
        for attr in ("homo", "lumo", "s1", "t1", "f", "dipole", "lambda_hole", "lambda_elec"):
            if not getattr(recipe, attr):
                setattr(recipe, attr, getattr(e, attr))

    return recipe


def parse_dataframe(df: pd.DataFrame) -> list[DeviceRecipe]:
    return [parse_row(row.to_dict(), i) for i, row in df.iterrows()]


def parse_csv(path: str, encoding: str = "utf-8-sig") -> list[DeviceRecipe]:
    from pathlib import Path
    p = Path(path)
    df = pd.read_excel(p) if p.suffix.lower() in (".xlsx", ".xls") \
        else pd.read_csv(p, encoding=encoding)
    return parse_dataframe(df)
