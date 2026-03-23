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


# ── 对比例变体策略 ────────────────────────────────────────────────────
import copy as _copy


class ComparisonStrategy:
    """
    对比例变体生成策略集合。
    每个策略接收原始 DeviceRecipe，返回 (变体 DeviceRecipe, 变更说明)。

    用法：
        variant, desc = ComparisonStrategy.replace_emitter(recipe, new_name="CBP")
        text = generate_text(variant, sections)
    """

    @staticmethod
    def replace_emitter(
        recipe: "DeviceRecipe",
        new_name: str = "",
        new_homo: str = "",
        new_lumo: str = "",
        comp_no: int = 1,
    ) -> tuple["DeviceRecipe", str]:
        """策略A：替换发光体（最常用）。"""
        v = _copy.deepcopy(recipe)
        v.device_no = f"对比例{comp_no}"
        old_names = [m.name for m in v.materials if m.role == "emitter"]
        for m in v.materials:
            if m.role == "emitter":
                m.name  = new_name or f"对比发光材料{comp_no}"
                m.homo  = new_homo
                m.lumo  = new_lumo
                m.s1 = m.t1 = m.f = m.dipole = m.lambda_hole = m.lambda_elec = ""
        # 清空顶层量化参数（来自旧 emitter）
        v.homo = new_homo; v.lumo = new_lumo
        v.s1 = v.t1 = v.f = v.dipole = v.lambda_hole = v.lambda_elec = ""
        old_str = "、".join(old_names) if old_names else "原发光材料"
        new_str = new_name or f"对比发光材料{comp_no}"
        return v, f"将发光层中的发光材料由{old_str}替换为{new_str}"

    @staticmethod
    def replace_host(
        recipe: "DeviceRecipe",
        new_name: str = "",
        comp_no: int = 1,
    ) -> tuple["DeviceRecipe", str]:
        """策略B：替换主体材料。"""
        v = _copy.deepcopy(recipe)
        v.device_no = f"对比例{comp_no}"
        old_names = [m.name for m in v.materials if m.role == "host"]
        for m in v.materials:
            if m.role == "host":
                m.name = new_name or f"对比主体材料{comp_no}"
                m.homo = m.lumo = ""
        old_str = "、".join(old_names) if old_names else "原主体材料"
        new_str = new_name or f"对比主体材料{comp_no}"
        return v, f"将发光层主体材料由{old_str}替换为{new_str}"

    @staticmethod
    def change_dopant_ratio(
        recipe: "DeviceRecipe",
        new_ratio: str,
        comp_no: int = 1,
    ) -> tuple["DeviceRecipe", str]:
        """策略C：改变发光体掺杂比例。"""
        v = _copy.deepcopy(recipe)
        v.device_no = f"对比例{comp_no}"
        old_ratios = [m.ratio for m in v.materials if m.role == "emitter" and m.ratio]
        for m in v.materials:
            if m.role == "emitter":
                m.ratio = new_ratio
            elif m.role == "host":
                try:
                    m.ratio = str(round(100 - float(new_ratio), 1))
                except ValueError:
                    pass
        old_str = "、".join(old_ratios) if old_ratios else "原比例"
        return v, f"将发光体掺杂浓度由{old_str} wt%调整为{new_ratio} wt%"

    @staticmethod
    def remove_layer(
        recipe: "DeviceRecipe",
        role: str,
        comp_no: int = 1,
    ) -> tuple["DeviceRecipe", str]:
        """策略D：去除某功能层（如去除 EBL / HIL）。"""
        from .constants import ROLE_LABELS
        v = _copy.deepcopy(recipe)
        v.device_no = f"对比例{comp_no}"
        removed = [m.name for m in v.materials if m.role == role]
        v.materials = [m for m in v.materials if m.role != role]
        role_label = ROLE_LABELS.get(role, role)
        removed_str = "、".join(removed) if removed else role_label
        return v, f"去除{role_label}（{removed_str}）"
