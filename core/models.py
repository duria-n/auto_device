"""core/models.py — 器件配方数据模型"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MaterialLayer:
    """单个功能层材料的参数"""
    id:            str = ""
    name:          str = ""
    role:          str = "htl"   # 见 constants.ROLE_ORDER
    thk:           str = ""      # 厚度 nm
    ratio:         str = ""      # 掺杂比例 wt%
    smiles:        str = ""
    homo:          str = ""
    lumo:          str = ""
    s1:            str = ""
    t1:            str = ""
    f:             str = ""
    dipole:        str = ""
    lambda_hole:   str = ""
    lambda_elec:   str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MaterialLayer":
        return cls(**{k: str(v) if v not in (None, "nan", "None") else ""
                      for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DeviceRecipe:
    """完整器件配方（一行 CSV = 一个 DeviceRecipe）"""
    device_no:   str = "实施例1"
    substrate:   str = "玻璃基板"
    anode:       str = "ITO"
    anode_thk:   str = ""
    cathode:     str = "Al"
    cathode_thk: str = ""
    # 量化参数（顶层，通常来自 emitter 层，备用）
    homo:        str = ""
    lumo:        str = ""
    s1:          str = ""
    t1:          str = ""
    f:           str = ""
    dipole:      str = ""
    lambda_hole: str = ""
    lambda_elec: str = ""
    # 器件性能（实测）
    von:         str = ""
    vop:         str = ""
    vth:         str = ""
    eqe:         str = ""
    cda:         str = ""
    ciex:        str = ""
    ciey:        str = ""
    el_peak:     str = ""
    t95:         str = ""
    lmax:        str = ""
    # 功能层列表（按阳极→阴极排列）
    materials: list[MaterialLayer] = field(default_factory=list)

    def get_emitters(self) -> list[MaterialLayer]:
        return [m for m in self.materials if m.role == "emitter"]

    def get_hosts(self) -> list[MaterialLayer]:
        return [m for m in self.materials if m.role == "host"]

    def get_non_eml(self) -> list[MaterialLayer]:
        return [m for m in self.materials if m.role not in ("host", "emitter")]
