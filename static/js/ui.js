// ui.js — DOM 渲染与交互逻辑
"use strict";

// ── Tab 切换 ──────────────────────────────────────────────────────────
function switchTab(tab) {
  document.getElementById("paneManual").style.display = tab === "manual" ? "" : "none";
  document.getElementById("paneBatch").style.display  = tab === "batch"  ? "" : "none";
  document.getElementById("tabManual").classList.toggle("active", tab === "manual");
  document.getElementById("tabBatch").classList.toggle("active",  tab === "batch");
}

// ── Settings 抽屉 ─────────────────────────────────────────────────────
function toggleSettings() {
  document.getElementById("settingsDrawer").classList.toggle("open");
}

// ── 生成模式切换 ──────────────────────────────────────────────────────
function setMode(mode) {
  State.mode = mode;
  ["template","polish","direct"].forEach(m => {
    document.getElementById(`mode${m.charAt(0).toUpperCase()+m.slice(1)}`)
            .classList.toggle("active", false);
  });
  const idMap = { template:"modeTemplate", template_polish:"modePolish", llm_direct:"modeDirect" };
  document.getElementById(idMap[mode]).classList.add("active");

  const needLLM = mode !== "template";
  document.getElementById("llmFields").style.display = needLLM ? "" : "none";

  const badges = { template:"模板引擎", template_polish:"模板+LLM润色", llm_direct:"LLM直写" };
  document.getElementById("modeBadge").textContent = badges[mode];
}

// ── Provider / Model 下拉 ─────────────────────────────────────────────
function onProviderChange() {
  const provider = document.getElementById("selProvider").value;
  State.llm.provider = provider;
  const isHF = provider === "huggingface";

  // 切换 HF 面板 vs API 面板
  document.getElementById("hfPanel").style.display    = isHF ? "" : "none";
  document.getElementById("apiModelRow").style.display= isHF ? "none" : "";
  document.getElementById("apiKeyRow").style.display  = isHF ? "none" : "";

  if (!isHF) {
    const models = PROVIDER_MODELS[provider] || [];
    const sel = document.getElementById("selModel");
    sel.innerHTML = models.map(m => `<option value="${m}">${m}</option>`).join("");
    State.llm.model = models[0] || "";
    const hints = {
      openai:    "platform.openai.com → API keys",
      anthropic: "console.anthropic.com → API Keys",
      qwen:      "dashscope.aliyun.com → API-KEY管理",
      deepseek:  "platform.deepseek.com → API keys",
    };
    document.getElementById("keyHint").textContent = hints[provider] || "";
  } else {
    // 加载推荐模型列表
    loadHfRecommended();
  }
}

// ── HuggingFace 交互 ──────────────────────────────────────────────────
function updateHfModel() {
  const modelId = document.getElementById("hfModelId").value.trim();
  State.llm.model = modelId;
  // 同步高亮推荐列表
  document.querySelectorAll(".hf-model-item").forEach(el => {
    el.classList.toggle("selected", el.dataset.id === modelId);
  });
}

function selectHfModel(modelId) {
  document.getElementById("hfModelId").value = modelId;
  State.llm.model = modelId;
  document.querySelectorAll(".hf-model-item").forEach(el => {
    el.classList.toggle("selected", el.dataset.id === modelId);
  });
}

async function loadHfRecommended() {
  const el = document.getElementById("hfRecommended");
  el.textContent = "加载中…";
  try {
    const resp = await fetch("/api/hf/recommended");
    const data = await resp.json();
    el.innerHTML = (data.models || []).map(m => `
      <div class="hf-model-item" data-id="${m.id}" onclick="selectHfModel('${m.id}')">
        <span class="hf-model-id">${m.id}</span>
        <span class="hf-model-desc">${m.desc}</span>
      </div>`).join("");
  } catch(e) {
    el.textContent = "加载失败";
  }
}

function _hfSetStatus(msg, type = "ok") {
  const el = document.getElementById("hfStatus");
  el.textContent = msg;
  el.className = `hf-status ${type}`;
  el.style.display = "block";
}

async function hfCheckCache() {
  const modelId  = document.getElementById("hfModelId").value.trim();
  const cacheDir = document.getElementById("hfCacheDir").value.trim();
  if (!modelId) { toast("请先填写模型 ID", true); return; }
  _hfSetStatus("检查本地缓存中…", "loading");
  try {
    const resp = await fetch("/api/hf/cache_status", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ model_id: modelId, cache_dir: cacheDir }),
    });
    const data = await resp.json();
    if (data.cached) {
      _hfSetStatus(`✓ ${modelId} 已在本地缓存，可直接使用`, "ok");
    } else {
      _hfSetStatus(`⚠ ${modelId} 本地未缓存，首次使用将自动下载`, "warn");
    }
  } catch(e) {
    _hfSetStatus("检查失败：" + e.message, "err");
  }
}

async function hfLoadModel() {
  const modelId  = document.getElementById("hfModelId").value.trim();
  const cacheDir = document.getElementById("hfCacheDir").value.trim();
  const device   = document.getElementById("hfDevice").value;
  const dtype    = document.getElementById("hfDtype").value;
  const load4bit = document.getElementById("hf4bit").checked;
  const load8bit = document.getElementById("hf8bit").checked;
  const hfToken  = document.getElementById("hfToken").value.trim();
  if (!modelId) { toast("请先填写模型 ID", true); return; }
  _hfSetStatus(`正在下载/加载 ${modelId}，首次可能需要数分钟…`, "loading");
  try {
    const resp = await fetch("/api/hf/load", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        model_id: modelId, cache_dir: cacheDir,
        device: device, dtype: dtype,
        load_in_4bit: load4bit, load_in_8bit: load8bit,
        hf_token: hfToken,
      }),
    });
    const data = await resp.json();
    if (data.success) {
      _hfSetStatus(`✓ ${modelId} 加载完成，已就绪`, "ok");
      State.llm.model = modelId;
      toast("✓ 模型加载完成");
    } else {
      _hfSetStatus("加载失败：" + data.error, "err");
    }
  } catch(e) {
    _hfSetStatus("网络错误：" + e.message, "err");
  }
}

async function hfUnloadModel() {
  const modelId = document.getElementById("hfModelId").value.trim() || null;
  _hfSetStatus("卸载中…", "loading");
  try {
    const resp = await fetch("/api/hf/unload", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ model_id: modelId }),
    });
    const data = await resp.json();
    _hfSetStatus(data.message || "已卸载", data.success ? "ok" : "err");
  } catch(e) {
    _hfSetStatus("卸载失败：" + e.message, "err");
  }
}

// ── TADF 自动检测 ─────────────────────────────────────────────────────
function autoMech() {
  const s1 = parseFloat(document.getElementById("s1").value);
  const t1 = parseFloat(document.getElementById("t1").value);
  const el = document.getElementById("mechTag");
  if (!isNaN(s1) && !isNaN(t1)) {
    const d = Math.abs(s1 - t1).toFixed(3);
    if (d < 0.3) {
      el.className = "mech-tag mech-tadf";
      el.textContent = `TADF ΔE=${d}`;
    } else {
      el.className = "mech-tag mech-conv";
      el.textContent = `荧光/磷光 ΔE=${d}`;
    }
  } else {
    el.className = "mech-tag";
    el.textContent = "—";
  }
}

// ── 功能层卡片渲染 ────────────────────────────────────────────────────
function renderMats() {
  const c = document.getElementById("matCards");
  c.innerHTML = "";
  State.materials.forEach((mat, idx) => {
    const rl = ROLE_LABELS[mat.role] || mat.role;
    const rc = "r-" + mat.role;
    const showRatio = mat.role === "host" || mat.role === "emitter";
    c.insertAdjacentHTML("beforeend", `
    <div class="mat-card" id="mc_${mat.id}">
      <div class="mat-card-hdr">
        <span class="role-badge ${rc}">${rl}</span>
        <div style="display:flex;gap:6px;align-items:center;">
          <span style="font-family:var(--mono);font-size:9px;color:var(--text-dim);">层序${idx+1}</span>
          <button class="btn-remove" onclick="removeMat(${mat.id})">✕</button>
        </div>
      </div>
      <div class="frow2">
        <div class="fg"><div class="fl">材料代号/名称</div>
          <input type="text" value="${mat.name}" placeholder="如 BP1"
            onchange="updateMat(${mat.id},'name',this.value)"></div>
        <div class="fg"><div class="fl">功能角色</div>
          <select onchange="updateMat(${mat.id},'role',this.value);renderMats()">
            ${Object.entries(ROLE_LABELS).map(([k,v])=>`<option value="${k}" ${mat.role===k?"selected":""}>${v}</option>`).join("")}
          </select></div>
      </div>
      <div class="frow${showRatio?3:2}">
        <div class="fg"><div class="fl">厚度 (nm)</div>
          <input type="text" value="${mat.thk}" placeholder="如 BP1THK=30"
            onchange="updateMat(${mat.id},'thk',this.value)"></div>
        <div class="fg"><div class="fl">HOMO (eV)</div>
          <input type="text" value="${mat.homo}" placeholder="-5.4"
            onchange="updateMat(${mat.id},'homo',this.value)"></div>
        ${showRatio?`<div class="fg"><div class="fl">掺杂比例 (wt%)</div>
          <input type="text" value="${mat.ratio}" placeholder="${mat.role==="emitter"?"3":"97"}"
            onchange="updateMat(${mat.id},'ratio',this.value)"></div>`:""}
      </div>
    </div>`);
  });
}

function updateMat(id, key, val) {
  const m = State.materials.find(m => m.id === id);
  if (m) m[key] = val;
}
function addMat() {
  State.materials.push({ id: State.matIdCounter++, name:"", role:"etl", thk:"", ratio:"",
    homo:"", lumo:"", s1:"", t1:"", f:"", dipole:"", lambda_hole:"", lambda_elec:"" });
  renderMats();
}
function removeMat(id) {
  State.materials = State.materials.filter(m => m.id !== id);
  renderMats();
}

// ── 输出区渲染 ────────────────────────────────────────────────────────
const PH_RE = /【待补充:[^】]+】/g;

function renderOutput(text) {
  State.lastText = text;
  const el = document.getElementById("outputBody");
  // 高亮占位符
  const html = text.replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(PH_RE, m => `<span class="ph">${m}</span>`);
  el.innerHTML = `<div class="out-block">${html}</div>`;

  // Stats
  const words = text.replace(/\s/g,"").length;
  const phCount = (text.match(PH_RE) || []).length;
  const secs = (text.match(/^[①②③④⑤⑥]/m) ? text.match(/^[①②③④⑤⑥]/gm).length : 0);
  document.getElementById("stWords").textContent = words;
  document.getElementById("stSecs").textContent  = secs;
  document.getElementById("stPH").textContent    = phCount;
  document.getElementById("statsBar").style.display = "flex";
}

function clearOut() {
  document.getElementById("outputBody").innerHTML = `
    <div class="output-empty">
      <div class="empty-icon">◈</div>
      <p>配置参数后点击生成</p>
      <p class="empty-sub">未填字段将以橙色占位符标注</p>
    </div>`;
  document.getElementById("statsBar").style.display = "none";
  State.lastText = "";
}

// ── 批量结果渲染 ──────────────────────────────────────────────────────
function renderBatch(results) {
  State.batchTexts = results.map(r => r.text);
  document.getElementById("batchCount").textContent = `共${results.length}条`;
  const list = document.getElementById("batchList");
  list.innerHTML = "";
  results.forEach((r, i) => {
    const highlighted = r.text
      .replace(/&/g,"&amp;").replace(/</g,"&lt;")
      .replace(PH_RE, m => `<span class="ph">${m}</span>`);
    list.insertAdjacentHTML("beforeend", `
    <div class="batch-item">
      <div class="batch-item-hdr" onclick="toggleBatch(${i})">
        <span class="batch-item-title">${r.device_no || "实施例"+r.index}</span>
        <span style="font-family:var(--mono);font-size:9px;color:var(--text-dim);">▾</span>
      </div>
      <div class="batch-item-body" id="bi_${i}">${highlighted}</div>
    </div>`);
  });
  document.getElementById("batchResultCard").style.display = "";
}

function toggleBatch(i) {
  document.getElementById(`bi_${i}`).classList.toggle("open");
}

// ── Toast ─────────────────────────────────────────────────────────────
function toast(msg, err = false) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "toast" + (err ? " err" : "");
  el.style.display = "block";
  clearTimeout(window._toast);
  window._toast = setTimeout(() => el.style.display = "none", 2800);
}

// ── Loading overlay ───────────────────────────────────────────────────
function showLoading(msg = "生成中…") {
  document.getElementById("loadingText").textContent = msg;
  document.getElementById("loadingOverlay").style.display = "flex";
}
function hideLoading() {
  document.getElementById("loadingOverlay").style.display = "none";
}

// ── 复制 / 导出 ───────────────────────────────────────────────────────
function copyOut() {
  if (!State.lastText) { toast("请先生成文本", true); return; }
  navigator.clipboard.writeText(State.lastText).then(() => toast("✓ 已复制到剪贴板"));
}

function validateKey() {
  const key = document.getElementById("inputApiKey").value.trim();
  if (!key) { toast("请先输入 API Key", true); return; }
  State.llm.api_key = key;
  State.llm.provider = document.getElementById("selProvider").value;
  State.llm.model    = document.getElementById("selModel").value;
  apiValidateKey(State.llm);
}

function saveKeyToEnv() {
  const key = document.getElementById("inputApiKey").value.trim();
  if (!key) { toast("请先输入 API Key", true); return; }
  apiSaveKey(document.getElementById("selProvider").value, key);
}
