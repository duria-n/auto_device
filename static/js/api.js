// api.js — 所有后端 fetch 请求封装
"use strict";

// ── 工具 ──────────────────────────────────────────────────────────────
function _llmPayload() {
  if (State.mode === "template") return {};

  const provider = State.llm.provider;
  const base = {
    llm: {
      provider:    provider,
      model:       State.llm.model || document.getElementById("selModel")?.value || "",
      max_tokens:  parseInt(document.getElementById("inputTokens")?.value || 2048),
      temperature: parseFloat(document.getElementById("inputTemp")?.value || 0.3),
    }
  };

  if (provider === "huggingface") {
    // HF 本地推理：不需要 api_key，但有额外字段
    Object.assign(base.llm, {
      hf_cache_dir:      document.getElementById("hfCacheDir")?.value?.trim() || "",
      hf_device:         document.getElementById("hfDevice")?.value  || "auto",
      hf_torch_dtype:    document.getElementById("hfDtype")?.value   || "auto",
      hf_load_in_4bit:   document.getElementById("hf4bit")?.checked  || false,
      hf_load_in_8bit:   document.getElementById("hf8bit")?.checked  || false,
      hf_token:          document.getElementById("hfToken")?.value?.trim() || "",
      hf_max_new_tokens: parseInt(document.getElementById("inputTokens")?.value || 2048),
      model:             document.getElementById("hfModelId")?.value?.trim() || State.llm.model,
    });
  } else {
    base.llm.api_key = document.getElementById("inputApiKey")?.value?.trim() || State.llm.api_key;
  }

  return base;
}

function _getSections(prefix = "chk") {
  return ["structure","material","fabrication","performance","mechanism","comparison"]
    .filter(s => document.getElementById(`${prefix}_${s}`)?.checked);
}

// ── 单条生成 ──────────────────────────────────────────────────────────
async function apiGenerate(data, sections) {
  const resp = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      data, sections,
      mode: State.mode,
      ..._llmPayload(),
    }),
  });
  const json = await resp.json();
  if (!json.success) throw new Error(json.error);
  return json.text;
}

// ── CSV 批量生成 ───────────────────────────────────────────────────────
async function apiBatch(file, sections) {
  const form = new FormData();
  form.append("file", file);
  form.append("sections", sections.join(","));
  form.append("mode", State.mode);
  if (State.mode !== "template") {
    const key = document.getElementById("inputApiKey")?.value?.trim() || "";
    form.append("api_key",     key);
    form.append("provider",    State.llm.provider);
    form.append("model",       State.llm.model);
    form.append("max_tokens",  document.getElementById("inputTokens")?.value || 4096);
    form.append("temperature", document.getElementById("inputTemp")?.value   || 0.3);
  }
  const resp = await fetch("/api/batch", { method: "POST", body: form });
  const json = await resp.json();
  if (!json.success) throw new Error(json.error);
  return json.results;
}

// ── 导出 TXT ──────────────────────────────────────────────────────────
async function apiExportTxt(texts, filename = "器件例专利文本.txt") {
  const resp = await fetch("/api/export_txt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texts }),
  });
  const blob = await resp.blob();
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click(); URL.revokeObjectURL(url);
}

// ── 验证 API Key ──────────────────────────────────────────────────────
async function apiValidateKey(llmCfg) {
  const statusEl = document.getElementById("keyStatus");
  statusEl.style.display = "none";
  try {
    showLoading("验证 API Key…");
    const resp = await fetch("/api/validate_key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider:   llmCfg.provider,
        model:      llmCfg.model,
        api_key:    llmCfg.api_key,
      }),
    });
    const json = await resp.json();
    statusEl.style.display = "block";
    if (json.valid) {
      statusEl.className = "key-status ok";
      statusEl.textContent = `✓ ${json.provider} · ${json.model} 连接成功`;
      State.llm.api_key = llmCfg.api_key;
    } else {
      statusEl.className = "key-status err";
      statusEl.textContent = `✗ ${json.error}`;
    }
  } catch(e) {
    statusEl.style.display = "block";
    statusEl.className = "key-status err";
    statusEl.textContent = "✗ 网络错误：" + e.message;
  } finally {
    hideLoading();
  }
}

// ── 保存 Key 到 .env ──────────────────────────────────────────────────
async function apiSaveKey(provider, apiKey) {
  try {
    const resp = await fetch("/api/save_key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, api_key: apiKey }),
    });
    const json = await resp.json();
    if (json.success) toast("✓ API Key 已写入 .env 文件，重启生效");
    else toast("写入失败：" + json.error, true);
  } catch(e) {
    toast("网络错误：" + e.message, true);
  }
}
