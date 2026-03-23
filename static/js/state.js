// state.js — 全局状态（所有 JS 模块共享）
"use strict";

const ROLE_LABELS = {
  hil:     "HIL 空穴注入层",
  htl:     "HTL 空穴传输层",
  ebl:     "EBL 电子阻挡层",
  host:    "EML 主体材料",
  emitter: "EML 发光体",
  hbl:     "HBL 空穴阻挡层",
  etl:     "ETL 电子传输层",
  eil:     "EIL 电子注入层",
};

const ROLE_ORDER = ["hil","htl","ebl","host","emitter","hbl","etl","eil"];

const PROVIDER_MODELS = {
  openai:    ["gpt-4o","gpt-4o-mini","gpt-4-turbo","gpt-3.5-turbo"],
  anthropic: ["claude-opus-4-5","claude-sonnet-4-5","claude-haiku-4-5-20251001"],
  qwen:      ["qwen-max","qwen-plus","qwen-turbo","qwen-long"],
  deepseek:  ["deepseek-chat","deepseek-reasoner"],
};

// ── App state ────────────────────────────────────────────────────────
const State = {
  // 生成模式
  mode: "template",    // "template" | "template_polish" | "llm_direct"

  // LLM 配置（界面级，优先于 .env）
  llm: {
    provider:    "openai",
    model:       "gpt-4o",
    api_key:     "",
    max_tokens:  4096,
    temperature: 0.3,
  },

  // 功能层列表
  materials: [
    { id: 1, name:"HATCN",  role:"hil",    thk:"10", ratio:"",  homo:"", lumo:"", s1:"", t1:"", f:"", dipole:"", lambda_hole:"", lambda_elec:"" },
    { id: 2, name:"NPB",    role:"htl",    thk:"40", ratio:"",  homo:"", lumo:"", s1:"", t1:"", f:"", dipole:"", lambda_hole:"", lambda_elec:"" },
    { id: 3, name:"",       role:"host",   thk:"30", ratio:"97",homo:"", lumo:"", s1:"", t1:"", f:"", dipole:"", lambda_hole:"", lambda_elec:"" },
    { id: 4, name:"",       role:"emitter",thk:"",   ratio:"3", homo:"", lumo:"", s1:"", t1:"", f:"", dipole:"", lambda_hole:"", lambda_elec:"" },
    { id: 5, name:"Liq",    role:"etl",    thk:"30", ratio:"",  homo:"", lumo:"", s1:"", t1:"", f:"", dipole:"", lambda_hole:"", lambda_elec:"" },
  ],
  matIdCounter: 6,

  // 批量上传
  uploadedFile: null,
  batchTexts: [],

  // 生成结果
  lastText: "",
};
