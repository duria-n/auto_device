"""core/parser.py — 将 CSV 行 / dict 解析为 DeviceRecipe"""
from __future__ import annotations
import re
import logging
from typing import Any
import pandas as pd
from .models import DeviceRecipe, MaterialLayer
from .constants import ROLE_ORDER

logger = logging.getLogger(__name__)

# ── 带单位的数值提取（如 "-5.4eV", "30nm", "0.15 eV"）───────────────
_NUM_RE = re.compile(r"[-+]?\d+\.?\d*")


def _clean(v: Any) -> str:
    """将任意值转为干净字符串，过滤 nan/None/空。"""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "") else s


def _extract_number(v: Any) -> str:
    """
    提取字符串中的数值部分，处理带单位的实验数据。
    例："-5.4eV" → "-5.4"，"30 nm" → "30"，"0.15eV" → "0.15"
    原始值已是纯数字则直接返回；无法提取则返回原值（保留给占位符逻辑）。
    """
    s = _clean(v)
    if not s:
        return s
    # 已经是合法数字，直接返回
    try:
        float(s)
        return s
    except ValueError:
        pass
    # 尝试提取第一个数值（保留负号）
    m = re.search(r"[-+]?\d+\.?\d*", s)
    if m:
        extracted = m.group()
        logger.debug(f"[parser] 数值提取: {s!r} → {extracted!r}")
        return extracted
    return s   # 无法提取，原样返回（downstream 会生成占位符）


def _get(row: dict, *keys: str) -> str:
    """按优先级从 row 中取第一个非空值。"""
    for k in keys:
        v = _clean(row.get(k, ""))
        if v:
            return v
    return ""


def _get_num(row: dict, *keys: str) -> str:
    """取值并做数值提取（用于 HOMO/LUMO/S1/T1 等数值字段）。"""
    raw = _get(row, *keys)
    return _extract_number(raw) if raw else ""


def _check_bp_continuity(bp_ids: list[str]) -> None:
    """
    校验 BPn 编号连续性，跳号时输出警告（不中断流程）。
    例：有 BP1/BP3 但无 BP2 → 警告用户可能漏填了功能层。
    """
    nums = sorted(int(re.sub(r"\D", "", bp)) for bp in bp_ids)
    expected = list(range(nums[0], nums[-1] + 1)) if nums else []
    actual   = nums
    missing  = sorted(set(expected) - set(actual))
    if missing:
        logger.warning(
            f"[parser] 检测到 BP 编号跳号，缺少: {['BP'+str(n) for n in missing]}。"
            f"  已有: {['BP'+str(n) for n in actual]}。"
            f"  如非故意跳层，请检查 CSV 中对应的 BPnTHK 列是否填写。"
        )


def parse_row(row: dict[str, Any], row_idx: int = 0) -> DeviceRecipe:
    """将 CSV 一行 dict 解析为 DeviceRecipe。"""
    recipe = DeviceRecipe(
        device_no   = _get(row, "device_no")   or f"实施例{row_idx + 1}",
        substrate   = _get(row, "substrate")   or "玻璃基板",
        anode       = _get(row, "anode")       or "ITO",
        anode_thk   = _extract_number(_get(row, "anode_thk", "ITO_THK")),
        cathode     = _get(row, "cathode")     or "Al",
        cathode_thk = _extract_number(_get(row, "cathode_thk", "Al_THK")),
        von         = _get_num(row, "Von",  "von"),
        vop         = _get_num(row, "Vop",  "vop"),
        vth         = _get_num(row, "Vth",  "vth"),
        eqe         = _get_num(row, "EQE",  "eqe"),
        cda         = _get_num(row, "CdA",  "cd/A", "CE", "C.E"),
        ciex        = _get_num(row, "CIEx", "ciex"),
        ciey        = _get_num(row, "CIEy", "ciey"),
        el_peak     = _get_num(row, "EL_peak", "el_peak"),
        t95         = _get_num(row, "T95",  "T95(H)"),
        lmax        = _get_num(row, "Lmax", "lmax"),
    )

    bp_re = re.compile(r'^(BP\d+)THK$', re.IGNORECASE)
    bp_ids = sorted(
        {m.group(1).upper() for col in row if (m := bp_re.match(col))},
        key=lambda x: int(re.sub(r'\D', '', x))
    )

    if len(bp_ids) > 1:
        _check_bp_continuity(bp_ids)

    for bp in bp_ids:
        mat = MaterialLayer(
            id           = bp,
            name         = _get(row, f"{bp}_name", bp),
            role         = _get(row, f"{bp}_role") or "htl",
            thk          = _extract_number(_get(row, f"{bp}THK")),
            ratio        = _extract_number(_get(row, f"{bp}_ratio")),
            smiles       = _get(row, f"{bp}_SMILES", f"{bp}_smiles"),
            homo         = _get_num(row, f"{bp}_HOMO",   f"{bp}_homo"),
            lumo         = _get_num(row, f"{bp}_LUMO",   f"{bp}_lumo"),
            s1           = _get_num(row, f"{bp}_S1",     f"{bp}_s1"),
            t1           = _get_num(row, f"{bp}_T1",     f"{bp}_t1"),
            f            = _get_num(row, f"{bp}_f",      f"{bp}_F"),
            dipole       = _get_num(row, f"{bp}_Dipole", f"{bp}_dipole"),
            lambda_hole  = _get_num(row, f"{bp}_Lambda_hole",     f"{bp}_lambda_hole"),
            lambda_elec  = _get_num(row, f"{bp}_Lambda_electron", f"{bp}_lambda_electron"),
        )
        recipe.materials.append(mat)

    def _role_idx(m: MaterialLayer) -> int:
        try:   return ROLE_ORDER.index(m.role)
        except ValueError: return 99

    recipe.materials.sort(key=_role_idx)

    for e in recipe.get_emitters():
        for attr in ("homo","lumo","s1","t1","f","dipole","lambda_hole","lambda_elec"):
            if not getattr(recipe, attr):
                setattr(recipe, attr, getattr(e, attr))
        break

    return recipe



def parse_dataframe(df: pd.DataFrame) -> list[DeviceRecipe]:
    return [parse_row(row.to_dict(), i) for i, row in df.iterrows()]


def parse_csv(path: str, encoding: str = "utf-8-sig") -> list[DeviceRecipe]:
    from pathlib import Path
    p = Path(path)
    df = pd.read_excel(p) if p.suffix.lower() in (".xlsx", ".xls") \
        else pd.read_csv(p, encoding=encoding)
    return parse_dataframe(df)
