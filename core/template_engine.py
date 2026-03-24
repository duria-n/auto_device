"""core/template_engine.py — 纯规则模板引擎（不调用 LLM）"""
from __future__ import annotations
from .models import DeviceRecipe, MaterialLayer, EMLConfig
from .constants import ROLE_LABELS, ROLE_ORDER, EML_ROLES, TADF_THRESHOLD


# ── 占位符 ────────────────────────────────────────────────────────────
def ph(label: str) -> str:
    return f"【待补充:{label}】"


def val(v: str, label: str, unit: str = "") -> str:
    return f"{v}{unit}" if (v and v.strip()) else ph(label)


# ── 机制判断 ──────────────────────────────────────────────────────────
def detect_mechanism(s1: str, t1: str) -> tuple[str, float | None]:
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
# EML 描述构建（支持所有体系类型）
# ══════════════════════════════════════════════════════════════════════

def _fmt_ratio(m: MaterialLayer) -> str:
    return f"{m.ratio} wt%" if m.ratio else ph(f"{m.name or m.id}掺杂比例wt%")


def _eml_host_str(hosts: list[MaterialLayer]) -> str:
    """格式化主体材料描述，支持单主体和多主体。"""
    if not hosts:
        return ""
    if len(hosts) == 1:
        h = hosts[0]
        return f"以{h.name or ph('Host名称')}（{_fmt_ratio(h)}）为主体材料"
    parts = "、".join(
        f"{h.name or ph(f'Host{i+1}名称')}（{_fmt_ratio(h)}）"
        for i, h in enumerate(hosts)
    )
    return f"以{parts}为{'双' if len(hosts)==2 else '多元'}主体材料"


def _eml_dopant_str(
    sensitizers: list[MaterialLayer],
    emitters: list[MaterialLayer],
) -> str:
    """格式化掺杂组分描述（敏化剂 + 发光体），全部遍历。"""
    parts = []
    for i, s in enumerate(sensitizers):
        label = "敏化剂" if len(sensitizers) == 1 else f"敏化剂{i+1} "
        parts.append(f"{label}{s.name or ph(f'Sensitizer{i+1}名称')}（{_fmt_ratio(s)}）")
    for i, e in enumerate(emitters):
        label = "发光体" if len(emitters) == 1 else f"发光体{i+1} "
        parts.append(f"{label}{e.name or ph(f'Emitter{i+1}名称')}（{_fmt_ratio(e)}）")
    return "、".join(parts)


def _eml_structure_line(eml: EMLConfig, idx: int) -> tuple[str, int]:
    """
    生成 EML 叠层结构描述行，完整遍历所有 hosts/sensitizers/emitters。
    不截断任何组分，支持任意数量组合。
    """
    thk = val(eml.total_thk, "EML厚度/nm", " nm")
    t   = eml.system_type

    if t == "neat":
        if len(eml.emitters) == 1:
            e = eml.emitters[0]
            desc = f"发光层（EML）：{e.name or ph('Emitter名称')}，厚度为{thk}；"
        else:
            parts = "、".join(
                f"{e.name or ph(f'Emitter{i+1}名称')}（{_fmt_ratio(e)}）"
                for i, e in enumerate(eml.emitters)
            )
            desc = f"发光层（EML）：{parts}共蒸发形成发光层，厚度为{thk}；"
    else:
        host_str   = _eml_host_str(eml.hosts)
        dopant_str = _eml_dopant_str(eml.sensitizers, eml.emitters)
        connector  = "，掺杂" if host_str and dopant_str else ""
        suffix     = "，形成敏化型发光层" if eml.sensitizers else ""
        desc = f"发光层（EML）：{host_str}{connector}{dopant_str}{suffix}，厚度为{thk}；"

    return f"（{idx}）{desc}", idx + 1


def _eml_fabrication_steps(eml: EMLConfig, step: int) -> tuple[list[str], int]:
    """
    生成 EML 制备工艺步骤，完整遍历所有组分。
    """
    thk  = val(eml.total_thk, "EML厚度/nm", " nm")
    rate = ph("蒸镀速率Å/s")
    t    = eml.system_type
    lines = []

    if t == "neat":
        all_names = "、".join(
            e.name or ph(f"Emitter{i+1}名称") for i, e in enumerate(eml.emitters)
        )
        lines.append(
            f"（{step}）蒸镀{all_names}形成发光层，厚度{thk}，蒸镀速率{rate}；"
        )
    else:
        # 所有组分汇总：hosts + sensitizers + emitters，全部参与共蒸发
        host_parts = "、".join(
            f"{h.name or ph(f'Host{i+1}名称')}（{_fmt_ratio(h)}）"
            for i, h in enumerate(eml.hosts)
        )
        dopant_parts = _eml_dopant_str(eml.sensitizers, eml.emitters)

        all_parts = "、".join(filter(None, [host_parts, dopant_parts]))
        suffix = "敏化型" if eml.sensitizers else ("多元掺杂" if len(eml.emitters) > 1 else "")
        lines.append(
            f"（{step}）以{rate}速率共蒸发{all_parts}，"
            f"形成{suffix}发光层，厚度{thk}；"
        )

    step += 1
    return lines, step


# ══════════════════════════════════════════════════════════════════════
# 各段落生成函数
# ══════════════════════════════════════════════════════════════════════

def _build_structure(r: DeviceRecipe) -> str:
    lines = ["本实施例制备了一种有机电致发光器件，其叠层结构自下而上依次为：\n"]
    idx = 1
    eml = r.get_eml_config()

    lines.append(f"（{idx}）基板：{r.substrate}；"); idx += 1
    lines.append(
        f"（{idx}）阳极：{r.anode}，"
        f"厚度为{val(r.anode_thk, 'ITO厚度/nm', ' nm')}；"
    ); idx += 1

    non_eml = r.get_non_eml()

    # 已知合法 role 集合（不含 EML_ROLES）
    KNOWN_ANODE_ROLES   = {"hil", "htl", "ebl"}
    KNOWN_CATHODE_ROLES = {"hbl", "etl", "eil"}
    KNOWN_ROLES = KNOWN_ANODE_ROLES | KNOWN_CATHODE_ROLES

    # 阳极侧：仅选合法阳极侧 role，按层序排列
    anode_side = sorted(
        [m for m in non_eml if m.role in KNOWN_ANODE_ROLES],
        key=lambda m: _role_idx(m.role)
    )
    for m in anode_side:
        lines.append(
            f"（{idx}）{ROLE_LABELS.get(m.role, m.role)}："
            f"{m.name or ph('材料名称')}，"
            f"厚度为{val(m.thk, (m.name or '材料') + 'THK', ' nm')}；"
        ); idx += 1

    # EML（所有体系类型）
    if not eml.is_empty:
        eml_line, idx = _eml_structure_line(eml, idx)
        lines.append(eml_line)

    # 阴极侧：仅选合法阴极侧 role，按层序排列
    cathode_side = sorted(
        [m for m in non_eml if m.role in KNOWN_CATHODE_ROLES],
        key=lambda m: _role_idx(m.role)
    )
    for m in cathode_side:
        lines.append(
            f"（{idx}）{ROLE_LABELS.get(m.role, m.role)}："
            f"{m.name or ph('材料名称')}，"
            f"厚度为{val(m.thk, (m.name or '材料') + 'THK', ' nm')}；"
        ); idx += 1

    # 未知 role：独立追加到阴极前，并生成告警占位符（不混入正常分类）
    unknown = [m for m in non_eml if m.role not in KNOWN_ROLES]
    for m in unknown:
        lines.append(
            f"（{idx}）{ph(f'未知功能层角色[{m.role}]，请确认并修正')}："
            f"{m.name or ph('材料名称')}，"
            f"厚度为{val(m.thk, (m.name or '材料') + 'THK', ' nm')}；"
        ); idx += 1

    lines.append(
        f"（{idx}）阴极：{r.cathode}，"
        f"厚度为{val(r.cathode_thk, '金属阴极厚度/nm', ' nm')}。"
    )
    return "\n".join(lines)


def _build_material(r: DeviceRecipe) -> str:
    mech, delta = detect_mechanism(r.s1, r.t1)
    eml = r.get_eml_config()

    # 发光机制介绍
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
        transport = (
            "空穴传输特性优于电子传输特性，呈空穴型传输偏向" if lh < le else
            "电子传输特性优于空穴传输特性，呈电子型传输偏向" if le < lh else
            "空穴与电子传输性能相当，具有双极性传输特性"
        )
    except (ValueError, TypeError):
        transport = ph("载流子传输特性评价")

    delta_str = f"，单三重态能级差ΔE_ST = {delta} eV" if delta is not None else ""

    parts = [
        f"本实施例所用发光材料为{intro}。",
        f"所述发光材料的最高占据分子轨道（HOMO）能级为"
        f"{val(r.homo, 'HOMO能级', 'eV')}，"
        f"最低未占据分子轨道（LUMO）能级为{val(r.lumo, 'LUMO能级', 'eV')}，"
        f"带隙Eg = {eg}。",
        f"最低单重激发态能级S₁为{val(r.s1, 'S1能级', 'eV')}，"
        f"最低三重激发态能级T₁为{val(r.t1, 'T1能级', 'eV')}{delta_str}。",
        f"该材料振子强度f = {val(r.f, '振子强度f')}，"
        f"分子偶极矩为{val(r.dipole, '偶极矩Debye', 'D')}。",
        f"空穴重组能λ_hole = {val(r.lambda_hole, 'λ_hole', 'eV')}，"
        f"电子重组能λ_electron = {val(r.lambda_elec, 'λ_electron', 'eV')}，"
        f"{transport}。",
    ]

    # 多发光体：逐一描述各 Emitter 的能级
    if len(eml.emitters) > 1:
        emitter_descs = "；".join(
            f"{e.name or ph(f'Emitter{i+1}名称')}"
            f"（HOMO = {val(e.homo, f'E{i+1}-HOMO', 'eV')}，"
            f"LUMO = {val(e.lumo, f'E{i+1}-LUMO', 'eV')}，"
            f"S₁ = {val(e.s1, f'E{i+1}-S1', 'eV')}，"
            f"T₁ = {val(e.t1, f'E{i+1}-T1', 'eV')}）"
            for i, e in enumerate(eml.emitters)
        )
        parts.append(
            f"本实施例采用多元发光体体系，各发光体能级分别为：{emitter_descs}；"
            f"多组分协同可实现{ph('颜色/光谱')}的宽谱发射。"
        )

    # 多主体：描述双主体体系的能级匹配
    if len(eml.hosts) > 1:
        host_descs = "；".join(
            f"{h.name or ph(f'Host{i+1}名称')}"
            f"（HOMO = {val(h.homo, f'H{i+1}-HOMO', 'eV')}，"
            f"LUMO = {val(h.lumo, f'H{i+1}-LUMO', 'eV')}）"
            for i, h in enumerate(eml.hosts)
        )
        parts.append(
            f"发光层采用{'双' if len(eml.hosts)==2 else '多元'}主体体系："
            f"{host_descs}；"
            f"多主体结构可有效平衡载流子注入，拓宽激子复合区域。"
        )

    return "\n\n".join(parts)


def _build_fabrication(r: DeviceRecipe) -> str:
    lines = [
        f"将{r.substrate}上预镀有{r.anode}薄膜"
        f"（厚度{val(r.anode_thk, 'ITO厚度/nm', ' nm')}）"
        f"的基板经清洗及{ph('表面处理方式')}处理{ph('处理时间/min')}分钟后，"
        f"置于真空蒸镀系统（本底真空度优于{ph('真空度/Pa')}），"
        f"依次蒸镀各功能层：\n"
    ]
    step     = 1
    eml      = r.get_eml_config()
    rate     = ph("蒸镀速率Å/s")
    eml_done = False

    KNOWN_ANODE_ROLES   = {"hil", "htl", "ebl"}
    KNOWN_CATHODE_ROLES = {"hbl", "etl", "eil"}
    KNOWN_ROLES = KNOWN_ANODE_ROLES | KNOWN_CATHODE_ROLES

    for m in r.materials:
        if m.role in EML_ROLES:
            continue

        # 到阴极侧合法层时插入 EML（只插一次，用标志位控制）
        if not eml_done and m.role in KNOWN_CATHODE_ROLES:
            if not eml.is_empty:
                eml_steps, step = _eml_fabrication_steps(eml, step)
                lines.extend(eml_steps)
            eml_done = True

        name = m.name or ph("材料名称")
        thk  = val(m.thk, (m.name or '材料') + 'THK', " nm")

        if m.role in KNOWN_ROLES:
            rl = ROLE_LABELS.get(m.role, "")
            lines.append(
                f"（{step}）蒸镀{rl}{name}，厚度{thk}，蒸镀速率{rate}；"
            )
        else:
            # 未知 role：生成告警占位符，不静默跳过
            lines.append(
                f"（{step}）蒸镀{ph(f'未知功能层角色[{m.role}]')} {name}，"
                f"厚度{thk}，蒸镀速率{rate}；"
            )
        step += 1

    # EML 后无阴极侧层时（如 neat 器件或 EML 是最后功能层）补充插入
    if not eml_done and not eml.is_empty:
        eml_steps, step = _eml_fabrication_steps(eml, step)
        lines.extend(eml_steps)

    lines.append(
        f"（{step}）蒸镀{r.cathode}阴极，"
        f"厚度{val(r.cathode_thk, '金属阴极厚度/nm', ' nm')}；"
    )
    step += 1
    lines.append(
        f"（{step}）在{ph('封装气氛（N₂/Ar）')}手套箱中封装，"
        f"固化条件{ph('固化条件')}。"
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
            f"远小于0.3 eV的TADF判断阈值，表明该材料具有热活化延迟荧光"
            f"（TADF）特性。\n\n"
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


def _build_comparison(
    r: DeviceRecipe,
    comparisons: list[tuple["DeviceRecipe", str]] | None = None,
) -> str:
    """
    生成对比例段落。

    Parameters
    ----------
    r           : 原始实施例
    comparisons : [(变体DeviceRecipe, 变更说明), ...] 列表
                  为 None 时生成全占位符版本（旧行为，向后兼容）
    """
    if not comparisons:
        # 无对比例数据，全占位符
        change_ph = ph("变更说明（如：将发光层中的发光材料替换为XXX）")
        return (
            f"对比例1\n\n"
            f"除{change_ph}外，"
            f"其余结构与制备方法与{r.device_no}相同，制备对比器件。\n\n"
            f"测试结果显示，对比例器件的外量子效率EQEmax为{ph('对比EQE/%')}，"
            f"启亮电压Von为{ph('对比Von')} V，寿命T95为{ph('对比T95')} h。\n\n"
            f"与对比例相比，本{r.device_no}所用材料在保持"
            f"{ph('颜色/光谱')}发光特性的同时，"
            f"外量子效率提升约{ph('EQE提升比例')}%，寿命提升约{ph('寿命提升比例')}%，"
            f"充分证明了本发明所述{ph('技术特征')}的技术优势。"
        )

    blocks = []
    for variant, change_desc in comparisons:
        comp_no = variant.device_no   # 如 "对比例1"

        # 生成对比例的结构描述（只生成叠层结构段）
        comp_structure = _build_structure(variant)

        # 对比数据（有实测值则用，否则占位符）
        eqe_comp = val(variant.eqe, "对比EQE/%", "%")
        von_comp = val(variant.von, "对比Von", " V")
        t95_comp = val(variant.t95, "对比T95", " h")

        # 提升比例（有实测数据时可计算）
        eqe_improvement = ph("EQE提升比例")
        t95_improvement = ph("寿命提升比例")
        try:
            if r.eqe and variant.eqe:
                imp = round((float(r.eqe) - float(variant.eqe)) / float(variant.eqe) * 100, 1)
                eqe_improvement = str(imp)
        except (ValueError, TypeError):
            pass
        try:
            if r.t95 and variant.t95:
                imp = round((float(r.t95) - float(variant.t95)) / float(variant.t95) * 100, 1)
                t95_improvement = str(imp)
        except (ValueError, TypeError):
            pass

        block = (
            f"{comp_no}\n\n"
            f"{change_desc}，其余结构与制备方法与{r.device_no}相同，制备对比器件。\n\n"
            f"对比器件叠层结构如下：\n\n{comp_structure}\n\n"
            f"测试结果显示，{comp_no}器件的外量子效率EQEmax为{eqe_comp}，"
            f"启亮电压Von为{von_comp}，寿命T95为{t95_comp}。\n\n"
            f"与{comp_no}相比，本{r.device_no}的外量子效率提升约{eqe_improvement}%，"
            f"寿命提升约{t95_improvement}%，"
            f"充分证明了本发明所述{ph('技术特征')}的技术优势。"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


# ── 段落分发表 ────────────────────────────────────────────────────────
_SECTION_BUILDERS = {
    "structure":   ("① 器件叠层结构描述", _build_structure),
    "material":    ("② 各层材料性质描述", _build_material),
    "fabrication": ("③ 器件制备方法描述", _build_fabrication),
    "performance": ("④ 器件性能数据记述", _build_performance),
    "mechanism":   ("⑤ 发光机制分析说明", _build_mechanism),
    "comparison":  ("⑥ 与对比例效果对比", None),  # 特殊处理，见 generate_text
}


def generate_text(
    recipe: DeviceRecipe,
    sections: list[str],
    comparisons: list[tuple[DeviceRecipe, str]] | None = None,
) -> str:
    """
    模板引擎入口：返回纯文本（含占位符）。

    Parameters
    ----------
    recipe      : 主实施例配方
    sections    : 要生成的段落列表
    comparisons : 对比例列表，每项为 (变体配方, 变更说明)
                  由 ComparisonStrategy.xxx() 生成
                  为 None 时对比例段落全部使用占位符
    """
    parts = [recipe.device_no]
    for sec in sections:
        if sec not in _SECTION_BUILDERS:
            continue
        if sec == "comparison":
            title = "⑥ 与对比例效果对比"
            content = _build_comparison(recipe, comparisons)
        else:
            title, builder = _SECTION_BUILDERS[sec]
            content = builder(recipe)
        parts.append(f"{title}\n\n{content}")
    return "\n\n".join(parts)
