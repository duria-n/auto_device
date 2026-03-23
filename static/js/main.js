// main.js — 业务逻辑入口（依赖 state.js / ui.js / api.js 先加载）
"use strict";

// ── 收集手动输入数据 ──────────────────────────────────────────────────
function _collectData() {
  const g = id => document.getElementById(id)?.value?.trim() ?? "";
  return {
    device_no:   g("deviceNo"),
    substrate:   g("substrate"),
    anode:       g("anode"),
    anode_thk:   g("anodeTHK"),
    cathode:     g("cathode"),
    cathode_thk: g("cathodeTHK"),
    homo:        g("homo"),
    lumo:        g("lumo"),
    s1:          g("s1"),
    t1:          g("t1"),
    f:           g("fval"),
    dipole:      g("dipole"),
    lambda_hole: g("lambdaH"),
    lambda_elec: g("lambdaE"),
    von:         g("von"),
    vop:         g("vop"),
    vth:         "",
    eqe:         g("eqe"),
    cda:         g("cda"),
    ciex:        g("ciex"),
    ciey:        g("ciey"),
    el_peak:     g("elPeak"),
    t95:         g("t95"),
    lmax:        g("lmax"),
    materials:   State.materials.map(m => ({ ...m })),
  };
}

// ── 手动生成 ──────────────────────────────────────────────────────────
async function generateManual() {
  const sections = _getSections("chk");
  if (!sections.length) { toast("请至少选择一个生成段落", true); return; }

  // LLM 模式下校验 key
  if (State.mode !== "template") {
    const key = document.getElementById("inputApiKey")?.value?.trim();
    if (!key) { toast("LLM 模式需要填写 API Key", true); return; }
  }

  showLoading(State.mode === "template" ? "生成中…" : "LLM 处理中，请稍候…");
  try {
    const text = await apiGenerate(_collectData(), sections);
    renderOutput(text);
  } catch(e) {
    toast("生成失败：" + e.message, true);
  } finally {
    hideLoading();
  }
}

// ── 导出当前文本 ──────────────────────────────────────────────────────
async function exportTxt() {
  if (!State.lastText) { toast("请先生成文本", true); return; }
  await apiExportTxt([State.lastText]);
}

async function exportAllTxt() {
  if (!State.batchTexts.length) { toast("暂无批量结果", true); return; }
  await apiExportTxt(State.batchTexts, "器件例专利文本_批量.txt");
}

// ── 批量上传 & 生成 ───────────────────────────────────────────────────
let _uploadedFile = null;

function handleFile(input) {
  if (input.files[0]) _setFile(input.files[0]);
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById("dropZone").classList.remove("drag");
  if (e.dataTransfer.files[0]) _setFile(e.dataTransfer.files[0]);
}
function _setFile(file) {
  const ext = file.name.split(".").pop().toLowerCase();
  if (!["csv","xlsx","xls"].includes(ext)) { toast("仅支持 .csv / .xlsx 文件", true); return; }
  _uploadedFile = file;
  const info = document.getElementById("fileInfo");
  info.style.display = "block";
  info.textContent = `✓ ${file.name}  ·  ${(file.size/1024).toFixed(1)} KB`;
  document.getElementById("btnBatch").disabled = false;
}

async function runBatch() {
  if (!_uploadedFile) { toast("请先上传文件", true); return; }
  const sections = _getSections("bc");
  if (!sections.length) { toast("请至少选择一个段落", true); return; }
  if (State.mode !== "template") {
    const key = document.getElementById("inputApiKey")?.value?.trim();
    if (!key) { toast("LLM 模式需要填写 API Key", true); return; }
  }
  showLoading("批量生成中…");
  try {
    const results = await apiBatch(_uploadedFile, sections);
    renderBatch(results);
    toast(`✓ 成功生成 ${results.length} 条器件例`);
  } catch(e) {
    toast("批量生成失败：" + e.message, true);
  } finally {
    hideLoading();
  }
}

// ── 初始化 ────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  renderMats();
  onProviderChange();   // 初始化 model 下拉

  // 从服务端拉取 provider/model 列表（覆盖前端默认值）
  fetch("/api/providers").then(r => r.json()).then(data => {
    // 更新 PROVIDER_MODELS（state.js 中的）
    Object.assign(PROVIDER_MODELS, data.providers || {});
    onProviderChange();
  }).catch(() => {/* 静默失败，使用前端默认值 */});
});
