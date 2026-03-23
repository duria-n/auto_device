"""core/template_engine.py — 纯规则模板引擎（不调用 LLM）"""
from __future__ import annotations
import math
from .models import DeviceRecipe, MaterialLayer
from .constants import ROLE_LABELS, ROLE_ORDER, TADF_THRESHOLD


# ── 占位符 ────────────────────────────────────────────────────────────
def ph(label: str) -> str:
    return f"【待补充:{label}】"


def val(v: str, label: str, unit: str = "") -> str:
    return f"{v}{unit}" if v.strip() else ph(label)


# ── 机制判断 ──────────────────────────────────────────────────────────
def detect_mechanism(s1: str, t1: str) -> tuple[str, float | None]:
    """返回 ('TADF'|'conventional'|'unknown', delta|None)"""
    try:
        delta = abs(float(s1) - float(t1))
        return ("TADF" if delta < TADF_THRESHOLD else "conventional", round(delta, 3))
    except (ValueError, TypeError):
        return "unknown", None


def _role_idx(role: str) -> int:
    try:
        return ROLE_ORDER.index(role)
    except ValueError:
        return 99


# ══════════════════════════════════════════════════════════════════════
# 各段落生成函数
# ══════════════════════════════════════════════════════════════════════

def _build_structure(r: DeviceRecipe) -> str:
    lines = ["本实施例制备了一种有机电致发光器件，其叠层结构自下而上依次为：\n"]
    idx = 1

    lines.append(f"（{idx}）基板：{r.substrate}；"); idx += 1
    lines.append(
        f"（{idx}）阳极：{r.anode}，厚度为{val(r.anode_thk, 'ITO厚度/nm', ' nm')}；"
    ); idx += 1

    hosts    = r.get_hosts()
    emitters = r.get_emitters()
    non_eml  = r.get_non_eml()

    # HIL / HTL / EBL
    for m in non_eml:
        if _role_idx(m.role) >= _role_idx("host"):
            break
        lines.append(
            f"（{idx}）{ROLE_LABELS.get(m.role, m.role)}：{m.name or ph('材料名称')}，"
            f"厚度为{val(m.thk, (m.name or '材料') + 'THK', ' nm')}；"
        ); idx += 1

    # EML
    if hosts and emitters:
        h, e = hosts[0], emitters[0]
        lines.append(
            f"（{idx}）发光层（EML）：以{h.name or ph('Host名称')}为主体材料，"
            f"掺杂{e.name or ph('Emitter名称')}（掺杂浓度为{val(e.ratio, '掺杂浓度wt%', ' wt%')}），"
            f"厚度为{val(h.thk or e.thk, 'EML厚度/nm', ' nm')}；"
        ); idx += 1
    elif emitters:
        e = emitters[0]
        lines.append(
            f"（{idx}）发光层（EML）：{e.name or ph('Emitter名称')}，"
            f"厚度为{val(e.thk, 'EML厚度/nm', ' nm')}；"
        ); idx += 1

    # HBL / ETL / EIL
    for m in non_eml:
        if _role_idx(m.role) <= _role_idx("emitter"):
            continue
        lines.append(
            f"（{idx}）{ROLE_LABELS.get(m.role, m.role)}：{m.name or ph('材料名称')}，"
            f"厚度为{val(m.thk, (m.name or '材料') + 'THK', ' nm')}；"
        ); idx += 1

    lines.append(
        f"（{idx}）阴极：{r.cathode}，厚度为{val(r.cathode_thk, '金属阴极厚度/nm', ' nm')}。"
    )
    return "\n".join(lines)


def _build_material(r: DeviceRecipe) -> str:
    mech, delta = detect_mechanism(r.s1, r.t1)

    if mech == "TADF":
        intro = (
            f"热活化延迟荧光（TADF）材料，其单重态（S₁）与三重态（T₁）"
            f"能级差ΔE_ST = {delta} eV，满足高效反向系间窜越条件"
        )
    else:
        intro = ph("发光机制描述")

    # 带隙
    try:
        eg = f"{abs(float(r.lumo) - float(r.homo)):.2f} eV"
    except (ValueError, TypeError):
        eg = ph("带隙Eg/eV")

    # 载流子传输评价
    try:
        lh, le = float(r.lambda_hole), float(r.lambda_elec)
        if lh < le:
            transport = "空穴传输特性优于电子传输特性，呈空穴型传输偏向"
        elif le < lh:
            transport = "电子传输特性优于空穴传输特性，呈电子型传输偏向"
        else:
            transport = "空穴与电子传输性能相当，具有双极性传输特性"
    except (ValueError, TypeError):
        transport = ph("载流子传输特性评价")

    delta_str = f"，单三重态能级差ΔE_ST = {delta} eV" if delta is not None else ""

    return "\n\n".join([
        f"本实施例所用发光材料为{intro}。",
        f"所述发光材料的最高占据分子轨道（HOMO）能级为{val(r.homo, 'HOMO能级', 'eV')}，"
        f"最低未占据分子轨道（LUMO）能级为{val(r.lumo, 'LUMO能级', 'eV')}，"
        f"带隙Eg = {eg}。",
        f"最低单重激发态能级S₁为{val(r.s1, 'S1能级', 'eV')}，"
        f"最低三重激发态能级T₁为{val(r.t1, 'T1能级', 'eV')}{delta_str}。",
        f"该材料振子强度f = {val(r.f, '振子强度f')}，"
        f"分子偶极矩为{val(r.dipole, '偶极矩Debye', 'D')}。",
        f"空穴重组能λ_hole = {val(r.lambda_hole, 'λ_hole', 'eV')}，"
        f"电子重组能λ_electron = {val(r.lambda_elec, 'λ_electron', 'eV')}，"
        f"{transport}。",
    ])


def _build_fabrication(r: DeviceRecipe) -> str:
    lines = [
        f"将{r.substrate}上预镀有{r.anode}薄膜（厚度{val(r.anode_thk, 'ITO厚度/nm', ' nm')}）"
        f"的基板经清洗及{ph('表面处理方式')}处理{ph('处理时间/min')}分钟后，"
        f"置于真空蒸镀系统（本底真空度优于{ph('真空度/Pa')}），依次蒸镀各功能层：\n"
    ]
    step = 1
    hosts    = r.get_hosts()
    emitters = r.get_emitters()

    for m in r.materials:
        if m.role == "emitter":
            continue
        name = m.name or ph("材料名称")
        thk  = val(m.thk, (m.name or '材料') + 'THK', " nm")
        rate = ph("蒸镀速率Å/s")
        rl   = ROLE_LABELS.get(m.role, "")

        if m.role == "host" and emitters:
            e = emitters[0]
            ename = e.name or ph("Emitter名称")
            ratio = val(e.ratio, "掺杂浓度wt%", " wt%")
            eThk  = val(m.thk or e.thk, "EML厚度/nm", " nm")
            lines.append(
                f"（{step}）以{rate}速率共蒸发{name}与{ename}，"
                f"掺杂浓度{ratio}，厚度{eThk}；"
            )
        else:
            lines.append(f"（{step}）蒸镀{rl}{name}，厚度{thk}，蒸镀速率{rate}；")
        step += 1

    lines.append(
        f"（{step}）蒸镀{r.cathode}阴极，厚度{val(r.cathode_thk, '金属阴极厚度/nm', ' nm')}；"
    )
    step += 1
    lines.append(
        f"（{step}）在{ph('封装气氛（N₂/Ar）')}手套箱中封装，固化条件{ph('固化条件')}。"
    )
    return "\n".join(lines)


def _build_performance(r: DeviceRecipe) -> str:
    return "\n\n".join([
        "对所制备的器件进行电学及光学性能测试，结果如下：",
        f"启亮电压Von（@10⁻⁴ mA/cm²）为{val(r.von, 'Von启亮电压', 'V')}，"
        f"工作电压Vop为{val(r.vop, 'Vop工作电压', 'V')}，"
        f"阈值电压Vth为{val(r.vth, 'Vth', 'V')}。",
        f"器件最大外量子效率EQEmax为{val(r.eqe, 'EQE/%', '%')}，"
        f"电流效率CE为{val(r.cda, '电流效率cd/A', ' cd/A')}，"
        f"最大亮度Lmax为{val(r.lmax, '最大亮度cd/m²', ' cd/m²')}。",
        f"电致发光光谱峰值波长λ_EL = {val(r.el_peak, 'EL峰值波长', ' nm')}，"
        f"CIE色坐标为（{val(r.ciex, 'CIEx')}，{val(r.ciey, 'CIEy')}）。",
        f"在初始亮度{ph('初始亮度cd/m²')} cd/m²条件下，"
        f"器件寿命T95为{val(r.t95, 'T95寿命', ' h')}。",
    ])


def _build_mechanism(r: DeviceRecipe) -> str:
    mech, delta = detect_mechanism(r.s1, r.t1)
    s1s = val(r.s1, "S1能级", " eV")
    t1s = val(r.t1, "T1能级", " eV")
    fv  = val(r.f,  "振子强度f")

    if mech == "TADF":
        return (
            f"理论计算结果表明，所述发光材料的单重态能级S₁（{s1s}）"
            f"与三重态能级T₁（{t1s}）之间的能级差ΔE_ST = {delta} eV，"
            f"远小于0.3 eV的TADF判断阈值，表明该材料具有热活化延迟荧光（TADF）特性。\n\n"
            f"在此发光机制下，三重态激子（T₁）可通过热活化反向系间窜越（RISC）"
            f"转化为单重态激子（S₁）后辐射发光，理论内量子效率可接近100%。\n\n"
            f"振子强度f = {fv}，表明该材料跃迁偶极矩{ph('强弱评价')}，"
            f"有利于辐射跃迁速率的提升。"
        )
    return (
        f"所述发光材料的单重态能级S₁（{s1s}）与三重态能级T₁（{t1s}）"
        f"之间能级差{f'ΔE_ST = {delta} eV，' if delta else ph('ΔE_ST') + '，'}"
        f"该材料以{ph('发光机制（荧光/磷光）')}方式发光。\n\n"
        f"振子强度f = {fv}，器件中激子的辐射跃迁遵循{ph('跃迁类型')}规则。"
    )


def _build_comparison(r: DeviceRecipe) -> str:
    return (
        f"对比例1\n\n"
        f"除将发光层中的发光材料替换为{ph('对比材料名称')}外，"
        f"其余结构与制备方法与{r.device_no}相同，制备对比器件。\n\n"
        f"测试结果显示，对比例器件的外量子效率EQEmax为{ph('对比EQE/%')}，"
        f"启亮电压Von为{ph('对比Von')} V，寿命T95为{ph('对比T95')} h。\n\n"
        f"与对比例相比，本{r.device_no}所用发光材料在保持{ph('颜色/光谱')}发光特性的同时，"
        f"外量子效率提升约{ph('EQE提升比例')}%，寿命提升约{ph('寿命提升比例')}%，"
        f"充分证明了本发明所述{ph('技术特征')}的技术优势。"
    )


# ── 段落分发表 ────────────────────────────────────────────────────────
_SECTION_BUILDERS = {
    "structure":   ("① 器件叠层结构描述", _build_structure),
    "material":    ("② 各层材料性质描述", _build_material),
    "fabrication": ("③ 器件制备方法描述", _build_fabrication),
    "performance": ("④ 器件性能数据记述", _build_performance),
    "mechanism":   ("⑤ 发光机制分析说明", _build_mechanism),
    "comparison":  ("⑥ 与对比例效果对比", _build_comparison),
}


def generate_text(recipe: DeviceRecipe, sections: list[str]) -> str:
    """模板引擎入口：返回纯文本（含占位符）"""
    parts = [recipe.device_no]
    for sec in sections:
        if sec not in _SECTION_BUILDERS:
            continue
        title, builder = _SECTION_BUILDERS[sec]
        parts.append(f"{title}\n\n{builder(recipe)}")
    return "\n\n".join(parts)
