"""core/constants.py — 领域常量（角色/层序/占位符等）"""
from __future__ import annotations

ROLE_ORDER: list[str] = [
    "hil", "htl", "ebl", "host", "emitter", "hbl", "etl", "eil"
]

ROLE_LABELS: dict[str, str] = {
    "hil":     "HIL 空穴注入层",
    "htl":     "HTL 空穴传输层",
    "ebl":     "EBL 电子阻挡层",
    "host":    "EML 主体材料",
    "emitter": "EML 发光体",
    "hbl":     "HBL 空穴阻挡层",
    "etl":     "ETL 电子传输层",
    "eil":     "EIL 电子注入层",
}

DEFAULT_SECTIONS: list[str] = [
    "structure",
    "material",
    "fabrication",
    "performance",
    "mechanism",
    "comparison",
]

TADF_THRESHOLD = 0.3
