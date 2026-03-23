"""core/models.py — 器件配方数据模型"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .constants import EML_ROLES


@dataclass
class MaterialLayer:
    """单个功能层材料的参数"""
    id:            str = ""
    name:          str = ""
    role:          str = "htl"
    thk:           str = ""      # 厚度 nm
    ratio:         str = ""      # 掺杂比例 wt%（EML层使用）
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
        return cls(**{
            k: str(v) if v not in (None, "nan", "None") else ""
            for k, v in d.items()
            if k in cls.__dataclass_fields__
        })

    @property
    def is_eml(self) -> bool:
        return self.role in EML_ROLES


@dataclass
class EMLConfig:
    """
    EML 层的完整配置，支持多主体、多发光体、敏化剂。

    典型场景：
      单掺:   hosts=[H], emitters=[E]               H:E = 97:3
      双掺:   hosts=[H], emitters=[E1,E2]           H:E1:E2 = 60:20:20
      敏化:   hosts=[H], sensitizers=[S], emitters=[E]
      双主体: hosts=[H1,H2], emitters=[E]           H1:H2:E
      纯发光: hosts=[], emitters=[E]                无主体直接蒸镀
    """
    hosts:       list[MaterialLayer] = field(default_factory=list)
    sensitizers: list[MaterialLayer] = field(default_factory=list)
    emitters:    list[MaterialLayer] = field(default_factory=list)

    @property
    def all_materials(self) -> list[MaterialLayer]:
        return self.hosts + self.sensitizers + self.emitters

    @property
    def is_empty(self) -> bool:
        return not self.all_materials

    @property
    def total_thk(self) -> str:
        """取 EML 总厚度：优先用 host 厚度，否则用 emitter 厚度。"""
        for m in self.hosts + self.emitters:
            if m.thk:
                return m.thk
        return ""

    @property
    def system_type(self) -> str:
        """
        自动判断 EML 体系类型。
        返回值: 'single' | 'multi_emitter' | 'sensitized' | 'dual_host' | 'neat'

        判断优先级：
          1. 有敏化剂          → sensitized（不论 emitter 数量）
          2. 无主体             → neat
          3. ≥2 主体            → dual_host
          4. ≥2 发光体          → multi_emitter
          5. 其余               → single
        """
        nh = len(self.hosts)
        ns = len(self.sensitizers)
        ne = len(self.emitters)
        if ns > 0:
            return "sensitized"
        if nh == 0:
            return "neat"
        if nh >= 2:
            return "dual_host"
        if ne >= 2:
            return "multi_emitter"
        return "single"


@dataclass
class DeviceRecipe:
    """完整器件配方（一行 CSV = 一个 DeviceRecipe）"""
    device_no:   str = "实施例1"
    substrate:   str = "玻璃基板"
    anode:       str = "ITO"
    anode_thk:   str = ""
    cathode:     str = "Al"
    cathode_thk: str = ""
    # 顶层量化参数（通常从第一个 emitter 提升而来）
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

    # ── 快捷访问 ──────────────────────────────────────────────────────
    def get_emitters(self) -> list[MaterialLayer]:
        return [m for m in self.materials if m.role == "emitter"]

    def get_hosts(self) -> list[MaterialLayer]:
        return [m for m in self.materials if m.role == "host"]

    def get_sensitizers(self) -> list[MaterialLayer]:
        return [m for m in self.materials if m.role == "sensitizer"]

    def get_non_eml(self) -> list[MaterialLayer]:
        return [m for m in self.materials if m.role not in EML_ROLES]

    def get_eml_config(self) -> EMLConfig:
        """将所有 EML 层汇总为 EMLConfig 对象，供模板引擎使用。"""
        return EMLConfig(
            hosts       = self.get_hosts(),
            sensitizers = self.get_sensitizers(),
            emitters    = self.get_emitters(),
        )
