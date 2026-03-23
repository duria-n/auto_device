"""core/constants.py — 领域常量（角色/层序/占位符等）"""
from __future__ import annotations

# ── 层序（阳极 → 阴极）────────────────────────────────────────────────
# sensitizer：敏化剂，位于 host 与 emitter 之间（白光/敏化TADF常见）
ROLE_ORDER: list[str] = [
    "hil", "htl", "ebl",
    "host", "sensitizer", "emitter",
    "hbl", "etl", "eil"
]

ROLE_LABELS: dict[str, str] = {
    "hil":        "HIL 空穴注入层",
    "htl":        "HTL 空穴传输层",
    "ebl":        "EBL 电子阻挡层",
    "host":       "EML 主体材料",
    "sensitizer": "EML 敏化剂",
    "emitter":    "EML 发光体",
    "hbl":        "HBL 空穴阻挡层",
    "etl":        "ETL 电子传输层",
    "eil":        "EIL 电子注入层",
}

# EML 相关角色集合（用于统一判断）
EML_ROLES: frozenset[str] = frozenset({"host", "sensitizer", "emitter"})

DEFAULT_SECTIONS: list[str] = [
    "structure",
    "material",
    "fabrication",
    "performance",
    "mechanism",
    "comparison",
]

TADF_THRESHOLD = 0.3
