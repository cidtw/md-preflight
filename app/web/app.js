import {
  evaluateErrorUiState,
  formatApiError,
  restoreStepIndexAfterEvaluateError,
  sanitizeEvaluateParameters,
  validateStoreAddress,
} from "./wizard_logic.mjs";
import { initTheme } from "./theme.mjs";
import { exportReport } from "./report_export.mjs";
import {
  DEMO_SCENARIOS,
  VERIFIED_DEMO_STORES,
  getDemoScenario,
} from "./demo_scenarios.mjs";

/** @type {import("./demo_scenarios.mjs").DemoScenario[]} */
let liveVerifiedStores = [...VERIFIED_DEMO_STORES];
/** @type {string} */
let verifiedFilterChannel = "all";
import { mountStorePicker } from "./store_picker.mjs";
import { clearCompetitionSimCache, mountCompetitionSim } from "./competition_sim.mjs";

const EXPERT_KEY = "rop-expert-mode";

initTheme();

const form = document.getElementById("eval-form");
const inputPanel = document.getElementById("input-panel");
const loadingPanel = document.getElementById("loading-panel");
const resultPanel = document.getElementById("result-panel");
const formError = document.getElementById("form-error");
const submitBtn = document.getElementById("submit-btn");
const btnBack = document.getElementById("btn-back");
const btnNext = document.getElementById("btn-next");
const wizardNav = document.getElementById("wizard-nav");
const stepProgress = document.getElementById("step-progress");
const stepProgressList = document.getElementById("step-progress-list");
const welcomeStep = document.getElementById("step-welcome");
const comingSoon = document.getElementById("coming-soon");
const demoScenarioList = document.getElementById("demo-scenario-list");
const verifiedStoreList = document.getElementById("verified-store-list");
const verifiedStoreMeta = document.getElementById("verified-store-meta");
const verifiedStoreFilters = document.getElementById("verified-store-filters");

/** @type {object | null} */
let lastPayload = null;

/** @type {Record<string, unknown> | null} */
let lastParameters = null;

/** @type {Record<string, object>} */
let specsByKey = {};

/** @type {ReturnType<typeof mountStorePicker> | null} */
let storePicker = null;

const STEPS = [
  {
    id: "welcome",
    label: "환영",
    keys: [],
  },
  {
    id: "basic",
    label: "기본 정보",
    keys: ["store_type", "store_size", "avg_ticket"],
    el: () => document.getElementById("step-basic"),
  },
  {
    id: "detail",
    label: "세부 정보",
    keys: [
      "location_dong",
      "use_precise_location",
      "store_address",
      "consider_temp_foot_traffic",
      "consider_competition_saturation",
      "trade_area",
      "accessibility",
    ],
    el: () => document.getElementById("step-detail"),
  },
  {
    id: "inventory",
    label: "품목·운영",
    keys: [
      "product_name",
      "daily_demand",
      "standard_lead_time_days",
      "service_level",
      "order_day_pattern",
      "standard_rop",
      "demand_sigma_daily",
      "measured_logistics_delay_days",
    ],
    el: () => document.getElementById("step-inventory"),
  },
];

/** Index into STEPS. 0 = welcome */
let stepIndex = 0;

const DEFAULTS = {
  product_name: "냉장 간편식",
  store_type: "convenience",
  store_size: "cv_s",
  avg_ticket: "t_le_8k",
  location_dong: "서울시 마포구 서교동",
  use_precise_location: false,
  store_address: "",
  consider_temp_foot_traffic: false,
  consider_competition_saturation: false,
  trade_area: "office",
  accessibility: "indoor",
  daily_demand: 12,
  standard_lead_time_days: 2,
  service_level: "sl_95",
  order_day_pattern: "auto",
  // standard_rop left empty so comparison uses channel baseline when omitted
};

function fieldControl(spec) {
  if (spec.type === "boolean") {
    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = spec.key;
    input.id = `field-${spec.key}`;
    input.className = "checkbox-input";
    input.checked = Boolean(DEFAULTS[spec.key]);
    input.value = "true";
    return input;
  }
  if (spec.options && spec.options.length) {
    const select = document.createElement("select");
    select.name = spec.key;
    select.required = Boolean(spec.required);
    select.id = `field-${spec.key}`;
    for (const opt of spec.options) {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      if (DEFAULTS[spec.key] === opt.value) option.selected = true;
      select.appendChild(option);
    }
    return select;
  }
  const input = document.createElement("input");
  input.name = spec.key;
  input.id = `field-${spec.key}`;
  input.required = Boolean(spec.required);
  if (spec.type === "number") {
    input.type = "number";
    input.step = "any";
    if (spec.minimum != null) input.min = String(spec.minimum);
    if (spec.maximum != null) input.max = String(spec.maximum);
  } else {
    input.type = "text";
  }
  if (DEFAULTS[spec.key] != null && DEFAULTS[spec.key] !== "") {
    input.value = String(DEFAULTS[spec.key]);
  }
  if (spec.description) input.placeholder = spec.description;
  return input;
}

function mountField(spec, container) {
  // Custom combobox for precise store address (region cascade + Kakao search).
  if (spec.key === "store_address") {
    const host = document.createElement("div");
    host.dataset.fieldKey = "store_address";
    host.className = "store-picker-host";
    storePicker = mountStorePicker(host, {
      getStoreType: () => {
        const el = form?.elements.namedItem("store_type");
        return el && "value" in el ? String(el.value) : "";
      },
      onAddressSelected: ({ address, dongLabel }) => {
        if (storePicker) storePicker.setAddress(address);
        if (dongLabel) {
          const dongInput = form?.elements.namedItem("location_dong");
          if (dongInput && "value" in dongInput && !String(dongInput.value || "").trim()) {
            dongInput.value = dongLabel;
          }
        }
      },
    });
    container.appendChild(host);
    return;
  }

  const label = document.createElement("label");
  label.htmlFor = `field-${spec.key}`;
  label.dataset.fieldKey = spec.key;

  if (spec.type === "boolean") {
    label.className = "checkbox-label";
    const control = fieldControl(spec);
    label.appendChild(control);
    const title = document.createElement("span");
    title.className = "field-title";
    title.textContent = spec.label;
    label.appendChild(title);
    if (spec.description) {
      const hint = document.createElement("small");
      hint.className = "field-hint";
      hint.textContent = spec.description;
      label.appendChild(hint);
    }
    container.appendChild(label);
    if (spec.key === "use_precise_location") {
      control.addEventListener("change", syncPreciseLocationUI);
    }
    return;
  }

  const title = document.createElement("span");
  title.className = "field-title";
  title.textContent = spec.label + (spec.required ? "" : " (선택)");
  label.appendChild(title);
  // Always reserve a hint row so select controls align across the grid
  // (store_type has no description; store_size/avg_ticket do).
  const hint = document.createElement("small");
  hint.className = "field-hint";
  if (spec.description) {
    hint.textContent = spec.description;
  } else {
    hint.classList.add("is-empty");
    hint.textContent = "\u00a0";
  }
  label.appendChild(hint);
  label.appendChild(fieldControl(spec));
  container.appendChild(label);
}

function syncPreciseLocationUI() {
  const checkbox = form?.elements.namedItem("use_precise_location");
  const addressHost = form?.querySelector('[data-field-key="store_address"]');
  const addressInput =
    storePicker?.input || form?.elements.namedItem("store_address");
  const dongLabel = form?.querySelector('label[data-field-key="location_dong"]');
  const dongInput = form?.elements.namedItem("location_dong");
  const eventLabel = form?.querySelector(
    'label[data-field-key="consider_temp_foot_traffic"]',
  );
  const eventInput = form?.elements.namedItem("consider_temp_foot_traffic");
  const compLabel = form?.querySelector(
    'label[data-field-key="consider_competition_saturation"]',
  );
  const compInput = form?.elements.namedItem("consider_competition_saturation");
  const on = Boolean(checkbox && "checked" in checkbox && checkbox.checked);
  if (storePicker) {
    storePicker.setVisible(on);
  } else if (addressHost) {
    addressHost.hidden = !on;
  }
  if (addressInput && "required" in addressInput) {
    addressInput.required = on;
    if (!on && "value" in addressInput) addressInput.value = "";
  }
  // Precise path uses region cascade + place picker; hide manual 행정동 field.
  if (dongLabel) dongLabel.hidden = on;
  if (dongInput && "required" in dongInput) {
    dongInput.required = !on;
  }
  // Temporary foot-traffic / competition options only with a precise address.
  if (eventLabel) eventLabel.hidden = !on;
  if (eventInput && "checked" in eventInput) {
    eventInput.disabled = !on;
    if (!on) eventInput.checked = false;
  }
  if (compLabel) compLabel.hidden = !on;
  if (compInput && "checked" in compInput) {
    compInput.disabled = !on;
    if (!on) compInput.checked = false;
  }
}

async function buildForm() {
  const res = await fetch("/api/template");
  if (!res.ok) throw new Error(`template HTTP ${res.status}`);
  const template = await res.json();
  specsByKey = Object.fromEntries(template.parameters.map((p) => [p.key, p]));

  for (const mount of form.querySelectorAll(".field-mount")) {
    mount.innerHTML = "";
    const keys = (mount.dataset.keys || "").split(",").map((k) => k.trim()).filter(Boolean);
    for (const key of keys) {
      const spec = specsByKey[key];
      if (!spec) continue;
      mountField(spec, mount);
    }
  }

  stepProgressList.innerHTML = "";
  STEPS.filter((s) => s.id !== "welcome").forEach((s, i) => {
    const li = document.createElement("li");
    li.dataset.stepId = s.id;
    li.innerHTML = `<span class="step-num">${i + 1}</span><span class="step-label">${s.label}</span>`;
    stepProgressList.appendChild(li);
  });

  syncPreciseLocationUI();
  mountDemoScenarios();
  showStep(0);
}

/**
 * Fill form controls from a demo scenario parameter map.
 * @param {Record<string, string|number|boolean>} parameters
 */
function applyParametersToForm(parameters) {
  if (!form) return;
  for (const [key, value] of Object.entries(parameters)) {
    if (key === "store_address" && storePicker) {
      storePicker.setAddress(value == null ? "" : String(value));
      continue;
    }
    const el = form.elements.namedItem(key);
    if (!el) continue;
    if (el instanceof RadioNodeList) continue;
    if (el.type === "checkbox") {
      el.checked = Boolean(value);
      continue;
    }
    if (value === "" || value == null) {
      el.value = "";
      continue;
    }
    el.value = String(value);
  }
  syncPreciseLocationUI();
}

/**
 * @param {import("./demo_scenarios.mjs").DemoScenario} scenario
 * @param {"verified"|"explore"} tier
 */
function buildDemoCard(scenario, tier) {
  const card = document.createElement("article");
  card.className =
    tier === "verified" ? "demo-card demo-card-verified" : "demo-card demo-card-explore";
  card.dataset.scenarioId = scenario.id;
  const badge =
    tier === "verified"
      ? `<span class="demo-badge demo-badge-verified">검증 매장</span>`
      : `<span class="demo-badge demo-badge-explore">탐색·더미</span>`;
  const storeLine = scenario.storeLabel
    ? `<span class="demo-card-store">${escapeHtml(scenario.storeLabel)}</span>`
    : "";
  const note = scenario.verificationNote
    ? `<span class="demo-card-note">${escapeHtml(scenario.verificationNote)}</span>`
    : "";
  card.innerHTML = `
      ${badge}
      <span class="demo-card-title">${escapeHtml(scenario.title)}</span>
      ${storeLine}
      <span class="demo-card-blurb">${escapeHtml(scenario.blurb)}</span>
      <span class="demo-card-highlight">볼 포인트 · ${escapeHtml(scenario.highlight)}</span>
      ${note}
      <div class="demo-card-actions">
        <button type="button" class="btn btn-primary" data-demo-action="run">
          ${tier === "verified" ? "이 매장으로 분석" : "바로 분석"}
        </button>
        <button type="button" class="btn btn-ghost" data-demo-action="fill">입력만 채우기</button>
      </div>
    `;
  return card;
}

function bindDemoListClicks(host) {
  if (!host || host.dataset.demoBound === "1") return;
  host.dataset.demoBound = "1";
  host.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;
    const actionBtn = target.closest("[data-demo-action]");
    if (!actionBtn) return;
    const card = actionBtn.closest("[data-scenario-id]");
    const id = card?.getAttribute("data-scenario-id");
    const action = actionBtn.getAttribute("data-demo-action");
    if (!id || !action) return;
    void handleDemoScenario(id, action);
  });
}

/**
 * Map API VerifiedDemoStore → frontend demo card shape.
 * @param {Record<string, unknown>} row
 */
function mapApiStoreToScenario(row) {
  return {
    id: String(row.id || ""),
    tier: "verified",
    title: String(row.title || ""),
    storeLabel: String(row.store_label || row.storeLabel || ""),
    blurb: String(row.blurb || ""),
    highlight: String(row.highlight || ""),
    verificationNote: String(row.verification_note || row.verificationNote || ""),
    expected: row.expected && typeof row.expected === "object" ? row.expected : {},
    parameters:
      row.parameters && typeof row.parameters === "object" ? row.parameters : {},
    channel: String(row.channel || ""),
    distance_m: Number(row.distance_m || 0),
  };
}

function renderVerifiedStoreList() {
  if (!verifiedStoreList) return;
  verifiedStoreList.innerHTML = "";
  const list =
    verifiedFilterChannel === "all"
      ? liveVerifiedStores
      : liveVerifiedStores.filter((s) => s.channel === verifiedFilterChannel);
  if (!list.length) {
    const empty = document.createElement("p");
    empty.className = "mute";
    empty.textContent =
      "전수조사 결과가 없습니다. Kakao 키·앵커 조사 API를 확인하세요.";
    verifiedStoreList.appendChild(empty);
    return;
  }
  for (const store of list) {
    verifiedStoreList.appendChild(buildDemoCard(store, "verified"));
  }
}

function renderVerifiedFilters() {
  if (!verifiedStoreFilters) return;
  const channels = ["all", "convenience", "supermarket", "ssm", "hypermarket"];
  const labels = {
    all: "전체",
    convenience: "편의점 1km",
    supermarket: "슈퍼 3km",
    ssm: "SSM 3km",
    hypermarket: "대형 10km",
  };
  const counts = { all: liveVerifiedStores.length };
  for (const s of liveVerifiedStores) {
    const ch = s.channel || "other";
    counts[ch] = (counts[ch] || 0) + 1;
  }
  verifiedStoreFilters.hidden = liveVerifiedStores.length === 0;
  verifiedStoreFilters.innerHTML = channels
    .map((ch) => {
      const n = counts[ch] || 0;
      if (ch !== "all" && n === 0) return "";
      const active = verifiedFilterChannel === ch ? " is-active" : "";
      return `<button type="button" class="demo-filter-chip${active}" data-channel="${ch}">${labels[ch]} (${n})</button>`;
    })
    .join("");
  if (verifiedStoreFilters.dataset.filterBound !== "1") {
    verifiedStoreFilters.dataset.filterBound = "1";
    verifiedStoreFilters.addEventListener("click", (ev) => {
      const t = ev.target;
      if (!(t instanceof Element)) return;
      const btn = t.closest("[data-channel]");
      if (!btn) return;
      verifiedFilterChannel = btn.getAttribute("data-channel") || "all";
      renderVerifiedFilters();
      renderVerifiedStoreList();
    });
  }
}

async function loadLiveVerifiedStores() {
  try {
    // Prefer snapshot (fast). Live Kakao census is via /api/demo/survey-anchor.
    const res = await fetch("/api/demo/verified-stores?live=false");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const rows = await res.json();
    if (Array.isArray(rows) && rows.length) {
      liveVerifiedStores = rows.map(mapApiStoreToScenario).filter((s) => s.id);
    }
  } catch {
    // Keep bundled VERIFIED_DEMO_STORES fallback
    liveVerifiedStores = [...VERIFIED_DEMO_STORES];
  }
  if (verifiedStoreMeta) {
    verifiedStoreMeta.hidden = false;
    verifiedStoreMeta.textContent = liveVerifiedStores.length
      ? `조사 매장 ${liveVerifiedStores.length}곳 · 세솔로 25 앵커 · Kakao Local 전수조사`
      : "조사 결과 없음 — 스냅샷/API 키를 확인하세요.";
  }
}

async function mountDemoScenarios() {
  await loadLiveVerifiedStores();
  renderVerifiedFilters();
  renderVerifiedStoreList();
  bindDemoListClicks(verifiedStoreList);

  if (demoScenarioList) {
    demoScenarioList.innerHTML = "";
    for (const scenario of DEMO_SCENARIOS) {
      demoScenarioList.appendChild(buildDemoCard(scenario, "explore"));
    }
    bindDemoListClicks(demoScenarioList);
  }
}

/**
 * @param {string} id
 * @param {"run"|"fill"} action
 */
async function handleDemoScenario(id, action) {
  const scenario =
    liveVerifiedStores.find((s) => s.id === id) || getDemoScenario(id);
  if (!scenario || !form) return;
  applyParametersToForm(scenario.parameters);
  const isVerified = scenario.tier === "verified";
  if (action === "fill") {
    showStep(1);
    formError.hidden = false;
    formError.textContent = isVerified
      ? `검증 매장 「${scenario.title}」 프로필을 채웠습니다. 값을 확인한 뒤 분석하세요.`
      : `탐색 시나리오 「${scenario.title}」 입력을 채웠습니다. (더미/지도 탐색 경로)`;
    return;
  }
  // Jump to inventory so validate path matches normal submit, then evaluate.
  showStep(STEPS.length - 1);
  formError.hidden = true;
  await runEvaluate();
}

function showStep(index) {
  stepIndex = index;
  formError.hidden = true;

  const isWelcome = STEPS[index].id === "welcome";
  welcomeStep.hidden = !isWelcome;
  form.hidden = isWelcome;
  wizardNav.hidden = isWelcome;
  stepProgress.hidden = isWelcome;
  // Roadmap dummy only on landing welcome (hidden during wizard / loading / result).
  if (comingSoon) comingSoon.hidden = !isWelcome;

  for (const step of STEPS) {
    if (step.id === "welcome") continue;
    const el = step.el?.();
    if (el) el.hidden = step.id !== STEPS[index].id;
  }

  const activeId = STEPS[index].id;
  for (const li of stepProgressList.querySelectorAll("li")) {
    const id = li.dataset.stepId;
    li.classList.toggle("is-active", id === activeId);
    const order = STEPS.findIndex((s) => s.id === id);
    li.classList.toggle("is-done", order > 0 && order < index);
  }

  const isLast = index === STEPS.length - 1;
  btnBack.hidden = isWelcome;
  btnBack.disabled = false;
  // Only last step (inventory) shows submit; earlier steps use Next only.
  btnNext.hidden = isLast || isWelcome;
  submitBtn.hidden = !isLast || isWelcome;
  if (submitBtn) {
    submitBtn.disabled = !isLast || isWelcome;
    submitBtn.setAttribute("aria-hidden", isLast && !isWelcome ? "false" : "true");
  }

  if (!isWelcome) {
    const panel = STEPS[index].el?.();
    // Prefer controls in visible labels (store_address uses [hidden] on <label>).
    const focusable = panel?.querySelector(
      "label:not([hidden]) input:not([type=hidden]), label:not([hidden]) select",
    ) ?? panel?.querySelector(
      "input:not([type=hidden]):not([hidden]), select:not([hidden])",
    );
    focusable?.focus?.();
  }
}

function validateCurrentStep() {
  const step = STEPS[stepIndex];
  if (!step.keys.length) return true;

  const precise = form?.elements.namedItem("use_precise_location");
  const preciseOn = Boolean(precise && "checked" in precise && precise.checked);

  for (const key of step.keys) {
    if (key === "store_address" && !preciseOn) continue;
    if (key === "location_dong" && preciseOn) continue; // filled from region/place picker
    if (key === "consider_temp_foot_traffic" && !preciseOn) continue;
    if (key === "consider_competition_saturation" && !preciseOn) continue;
    const spec = specsByKey[key];
    if (!spec) continue;
    const el = form.elements.namedItem(key);
    if (!el) continue;

    if (spec.type === "boolean") continue;

    if (key === "store_address") {
      const value = "value" in el ? el.value : "";
      const check = validateStoreAddress(preciseOn, value);
      if (!check.ok) {
        formError.hidden = false;
        formError.textContent = check.message;
        el.focus?.();
        return false;
      }
      if (!preciseOn) continue;
    }

    if (typeof el.checkValidity === "function" && !el.checkValidity()) {
      el.reportValidity?.();
      return false;
    }
    if (spec.required) {
      const value = "value" in el ? String(el.value).trim() : "";
      if (!value) {
        formError.hidden = false;
        formError.textContent = `'${spec.label}' 항목을 입력해 주세요.`;
        el.focus?.();
        return false;
      }
    }
  }
  formError.hidden = true;
  return true;
}

function readParameters(formEl) {
  const parameters = {};
  const precise = formEl.elements.namedItem("use_precise_location");
  parameters.use_precise_location = Boolean(
    precise && "checked" in precise && precise.checked,
  );
  const eventOpt = formEl.elements.namedItem("consider_temp_foot_traffic");
  parameters.consider_temp_foot_traffic = Boolean(
    parameters.use_precise_location &&
      eventOpt &&
      "checked" in eventOpt &&
      eventOpt.checked,
  );
  const compOpt = formEl.elements.namedItem("consider_competition_saturation");
  parameters.consider_competition_saturation = Boolean(
    parameters.use_precise_location &&
      compOpt &&
      "checked" in compOpt &&
      compOpt.checked,
  );

  const data = new FormData(formEl);
  for (const [key, raw] of data.entries()) {
    if (
      key === "use_precise_location" ||
      key === "consider_temp_foot_traffic" ||
      key === "consider_competition_saturation"
    ) {
      continue;
    }
    if (raw === "" || raw == null) continue;
    const input = formEl.elements.namedItem(key);
    if (input && input.type === "number") {
      const asNum = Number(raw);
      if (!Number.isNaN(asNum)) {
        parameters[key] = asNum;
        continue;
      }
    }
    if (input && input.type === "checkbox") continue;
    parameters[key] = String(raw);
  }

  // Precise path: admin dong comes from region cascade / selected place.
  if (parameters.use_precise_location && storePicker) {
    const fromPicker = storePicker.getDongLabel?.() || "";
    if (fromPicker) {
      parameters.location_dong = fromPicker;
    } else if (!parameters.location_dong) {
      parameters.location_dong = "상세주소 기반";
    }
    const addr = storePicker.getAddress?.();
    if (addr) parameters.store_address = addr;
  }

  return sanitizeEvaluateParameters(parameters);
}

function fmt(n, digits = 1) {
  return Number(n).toLocaleString("ko-KR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function readExpertMode() {
  return localStorage.getItem(EXPERT_KEY) === "1";
}

function setExpertMode(on) {
  localStorage.setItem(EXPERT_KEY, on ? "1" : "0");
}

function pickNarrative(payload, expert) {
  const comparison =
    expert && payload.comparison_technical
      ? payload.comparison_technical
      : payload.comparison;
  const evidence =
    expert && payload.evidence_technical?.length
      ? payload.evidence_technical
      : payload.evidence;
  const recommendation =
    expert && payload.recommendation_technical
      ? payload.recommendation_technical
      : payload.recommendation;
  return { comparison, evidence, recommendation };
}

function findRow(comparison, ...needles) {
  return comparison.rows.find((r) =>
    needles.some((n) => String(r.metric).includes(n)),
  );
}

function statClass(delta) {
  if (delta > 0) return "is-up";
  if (delta < 0) return "is-down";
  return "";
}

function renderResult(payload, expertOverride) {
  lastPayload = payload;
  const expert =
    expertOverride !== undefined ? Boolean(expertOverride) : readExpertMode();
  const { comparison, evidence, recommendation } = pickNarrative(payload, expert);

  const guideHtml =
    payload.guidance && payload.guidance.length
      ? `<div class="guidance"><strong>입력 안내</strong><ul>${payload.guidance
          .map((g) => `<li>${escapeHtml(g)}</li>`)
          .join("")}</ul></div>`
      : "";

  const geo = payload.calc?.geo;
  let pathBadgeHtml = "";
  if (geo && geo.enabled) {
    if (geo.used_fallback) {
      pathBadgeHtml = `<div class="path-badge path-fallback" role="status">
        <strong>계산 경로</strong>
        <span>지도 보강 실패 → 행정동·상권 결정론 (used_fallback)</span>
      </div>`;
    } else {
      pathBadgeHtml = `<div class="path-badge path-geo" role="status">
        <strong>계산 경로</strong>
        <span>상세 주소 · 지도 POI 보강 반영</span>
      </div>`;
    }
  } else if (geo) {
    pathBadgeHtml = `<div class="path-badge path-dong" role="status">
      <strong>계산 경로</strong>
      <span>행정동·상권 파라미터 (상세 주소 미사용)</span>
    </div>`;
  }

  const s = payload.summary;
  const addressRow =
    s.use_precise_location && s.store_address
      ? `<dt>상세 주소</dt><dd>${escapeHtml(s.store_address)}</dd>`
      : "";
  const eventRow = s.consider_temp_foot_traffic
    ? `<dt>일시 유동 증분</dt><dd>반영 (반경 200m 행사·유동 시설)</dd>`
    : "";
  const compRow = s.consider_competition_saturation
    ? `<dt>경쟁 포화·수요 분산</dt><dd>반영 (업태별 1차 상권·경쟁 거리)</dd>`
    : "";

  const colStd = expert ? "표준" : "일반 기준";
  const colRec = expert ? "매장 맞춤" : "이 매장 추천";
  const colDelta = expert ? "Δ / 메모" : "어떻게 달라졌나";
  const evidenceTitle = expert
    ? "계산 근거 · 지식 베이스"
    : "왜 이렇게 나왔나요?";
  const cmpTitle = expert ? "ROP 비교" : "한눈에 보는 발주 기준";
  const layers = Array.isArray(payload.source_layers) ? payload.source_layers : [];
  const sourceLayersHtml =
    expert && layers.length
      ? `<div class="source-layers" aria-label="산출 근거 층">
          <div class="source-layers-head">
            <strong>산출 근거 층</strong>
            <span class="source-layers-hint">L1 이론 · L2 문헌 · L3 assumption</span>
          </div>
          <div class="source-layers-grid">
            ${layers
              .map(
                (row) => `<article class="source-layer-card layer-${escapeHtml(String(row.layer || "").toLowerCase())}">
                  <span class="layer-badge">${escapeHtml(row.layer || "")}</span>
                  <strong class="layer-title">${escapeHtml(row.title || "")}</strong>
                  <p class="layer-text">${escapeHtml(row.text || "")}</p>
                </article>`,
              )
              .join("")}
          </div>
        </div>`
      : "";

  const ropRow = findRow(comparison, "재발주", "ROP", "발주 시점");
  const ssRow = findRow(comparison, "여유 재고", "안전재고", "Safety");
  const qRow = findRow(comparison, "발주량", "Q");
  const cycleRow = findRow(comparison, "발주 요일", "주기");

  const rows = comparison.rows
    .map((r) => {
      const cls = r.delta > 0 ? "delta-up" : r.delta < 0 ? "delta-down" : "";
      return `<tr>
        <td>${escapeHtml(r.metric)}</td>
        <td>${fmt(r.standard_value)} ${escapeHtml(r.unit)}</td>
        <td><strong>${fmt(r.recommended_value)} ${escapeHtml(r.unit)}</strong></td>
        <td class="${cls}">${escapeHtml(r.delta_label)}</td>
      </tr>`;
    })
    .join("");

  const evidenceHtml = evidence
    .map(
      (block) => `<article class="evidence-card">
        <h3>${escapeHtml(block.title)}</h3>
        <p class="calc">${escapeHtml(block.calc_summary)}</p>
        <ul>${block.points.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul>
      </article>`,
    )
    .join("");

  resultPanel.innerHTML = `
    <div class="result-head">
      ${pathBadgeHtml}
      <label class="expert-toggle">
        <input type="checkbox" id="expert-mode" ${expert ? "checked" : ""} />
        <span>
          <strong>전문적인 해설 버전</strong>
          <small>전공·실무자용 공식·점수 표기 (Z, CAPA, FTI 등)</small>
        </span>
      </label>
      <div class="result-actions">
        <div class="export-menu" id="export-menu">
          <button type="button" class="btn btn-primary" id="export-btn" aria-haspopup="true" aria-expanded="false">
            리포트 내보내기
          </button>
          <div class="export-dropdown" id="export-dropdown" hidden role="menu">
            <button type="button" class="export-item" data-export="pdf" role="menuitem">PDF (인쇄 대화상자)</button>
            <button type="button" class="export-item" data-export="markdown" role="menuitem">Markdown (.md)</button>
            <button type="button" class="export-item" data-export="csv" role="menuitem">비교표 CSV (.csv)</button>
            <button type="button" class="export-item" data-export="json" role="menuitem">원본 JSON (.json)</button>
          </div>
        </div>
        <button type="button" class="btn btn-secondary" id="again-btn">처음부터 다시</button>
      </div>
    </div>

    <div class="verdict">
      <span class="v-label">추천 결과</span>
      ${escapeHtml(recommendation)}
    </div>
    ${guideHtml}

    <div class="stat-grid">
      <div class="stat-tile ${statClass(ropRow?.delta ?? 0)}">
        <div class="stat-value">${fmt(ropRow?.recommended_value ?? payload.calc.recommended_rop, 1)}</div>
        <div class="stat-label">발주 시점 재고 (개)</div>
      </div>
      <div class="stat-tile ${statClass(ssRow?.delta ?? 0)}">
        <div class="stat-value">${fmt(ssRow?.recommended_value ?? payload.calc.store_safety_stock, 1)}</div>
        <div class="stat-label">여유 재고 (개)</div>
      </div>
      <div class="stat-tile ${statClass(qRow?.delta ?? 0)}">
        <div class="stat-value">${fmt(qRow?.recommended_value ?? payload.calc.suggested_order_qty, 1)}</div>
        <div class="stat-label">1회 발주량 (개)</div>
      </div>
      <div class="stat-tile">
        <div class="stat-value">${escapeHtml(payload.calc.order_days_label || "—")}</div>
        <div class="stat-label">발주 요일 · ${fmt(cycleRow?.recommended_value ?? payload.calc.order_cycle_days, 1)}일 주기</div>
      </div>
    </div>

    <section class="result-section">
      <h2 class="section-title">매장 · 품목 요약</h2>
      <div class="summary-box">
        <dl class="summary-grid">
          <dt>분석 품목</dt><dd>${escapeHtml(s.product_name)}</dd>
          <dt>유형 / 규모</dt><dd>${escapeHtml(s.store_type_label)} / ${escapeHtml(s.store_size_label)}</dd>
          <dt>객단가</dt><dd>${escapeHtml(s.avg_ticket_label)}</dd>
          <dt>입지 / 접근성</dt><dd>${escapeHtml(s.location_dong)} / ${escapeHtml(s.accessibility_label)}</dd>
          ${addressRow}
          ${eventRow}
          ${compRow}
          <dt>상권</dt><dd>${escapeHtml(s.trade_area_label)}</dd>
          <dt>서비스 레벨</dt><dd>${escapeHtml(s.service_level_label || "-")}</dd>
          <dt>발주 패턴</dt><dd>${escapeHtml(s.order_day_pattern_label || "-")}</dd>
        </dl>
      </div>
    </section>

    <section class="result-section">
      <h2 class="section-title">${escapeHtml(cmpTitle)}</h2>
      <div class="table-wrap">
        <table class="cmp">
          <thead>
            <tr>
              <th>구분</th>
              <th>${escapeHtml(colStd)}</th>
              <th>${escapeHtml(colRec)}</th>
              <th>${escapeHtml(colDelta)}</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="rop-guide">${escapeHtml(comparison.rop_guidance)}</p>
    </section>

    <section class="result-section">
      <h2 class="section-title">
        ${escapeHtml(evidenceTitle)}
        <span class="count-chip">${evidence.length}</span>
      </h2>
      ${sourceLayersHtml}
      <div class="evidence-grid">${evidenceHtml}</div>
    </section>
    <section class="result-section" id="sim-mount"></section>
  `;
  resultPanel.hidden = false;
  if (comingSoon) comingSoon.hidden = true;
  document.getElementById("again-btn")?.addEventListener("click", () => {
    resultPanel.hidden = true;
    inputPanel.hidden = false;
    showStep(0);
  });
  document.getElementById("expert-mode")?.addEventListener("change", (ev) => {
    const on = Boolean(ev.target?.checked);
    setExpertMode(on);
    if (lastPayload) renderResult(lastPayload, on);
  });
  // Competition what-if simulator (uses last submitted parameters).
  const simMount = document.getElementById("sim-mount");
  if (simMount && lastParameters) {
    mountCompetitionSim(simMount, lastParameters, { expert });
  }
  // Export uses delegated listeners on #result-panel (see bindExportMenu).
  // Do not attach per-render — innerHTML replaces #export-btn each time.
}

/**
 * Export menu markup is injected by renderResult via resultPanel.innerHTML.
 * Bind once on the stable #result-panel with event delegation so clicks still
 * work after re-render (expert toggle) without stacking document listeners.
 */
/** @type {boolean} */
let exportMenuBound = false;

function closeExportMenu() {
  const dropdown = document.getElementById("export-dropdown");
  const btn = document.getElementById("export-btn");
  if (dropdown) dropdown.hidden = true;
  btn?.setAttribute("aria-expanded", "false");
}

function bindExportMenu() {
  if (exportMenuBound || !resultPanel) return;
  exportMenuBound = true;

  resultPanel.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;

    const exportItem = target.closest("[data-export]");
    if (exportItem && resultPanel.contains(exportItem)) {
      ev.preventDefault();
      ev.stopPropagation();
      const format = exportItem.getAttribute("data-export");
      if (!lastPayload || !format) {
        closeExportMenu();
        return;
      }
      const expertOn =
        document.getElementById("expert-mode")?.checked ?? readExpertMode();
      try {
        exportReport(format, lastPayload, { expert: expertOn });
      } catch (err) {
        window.alert(err instanceof Error ? err.message : String(err));
      } finally {
        closeExportMenu();
      }
      return;
    }

    const exportBtn = target.closest("#export-btn");
    if (exportBtn && resultPanel.contains(exportBtn)) {
      ev.stopPropagation();
      const dropdown = document.getElementById("export-dropdown");
      if (!dropdown) return;
      const willOpen = dropdown.hidden;
      dropdown.hidden = !willOpen;
      exportBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
    }
  });

  document.addEventListener("click", (ev) => {
    const menu = document.getElementById("export-menu");
    const dropdown = document.getElementById("export-dropdown");
    if (!menu || !dropdown || dropdown.hidden) return;
    const t = ev.target;
    if (t instanceof Node && !menu.contains(t)) closeExportMenu();
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") closeExportMenu();
  });
}

bindExportMenu();

document.getElementById("welcome-start")?.addEventListener("click", () => {
  showStep(1);
});

document.getElementById("nav-home")?.addEventListener("click", () => {
  resultPanel.hidden = true;
  loadingPanel.hidden = true;
  inputPanel.hidden = false;
  showStep(0);
});

btnBack?.addEventListener("click", () => {
  if (stepIndex <= 0) return;
  if (stepIndex === 1) {
    showStep(0);
    return;
  }
  showStep(stepIndex - 1);
});

btnNext?.addEventListener("click", () => {
  if (!validateCurrentStep()) return;
  if (stepIndex < STEPS.length - 1) showStep(stepIndex + 1);
});

function applyEvaluateErrorUi(message) {
  const ui = evaluateErrorUiState();
  loadingPanel.hidden = ui.loadingHidden;
  inputPanel.hidden = ui.inputHidden;
  stepProgress.hidden = ui.stepProgressHidden;
  formError.hidden = ui.formErrorHidden;
  formError.textContent = message;
  showStep(restoreStepIndexAfterEvaluateError(STEPS.length));
}

/**
 * Run evaluate from the current form state (wizard inventory or demo one-shot).
 * @param {{ skipStepGuard?: boolean }} [opts]
 */
async function runEvaluate(opts = {}) {
  if (!form) return;
  if (!opts.skipStepGuard && stepIndex !== STEPS.length - 1) {
    if (!validateCurrentStep()) return;
    if (stepIndex < STEPS.length - 1) showStep(stepIndex + 1);
    return;
  }
  if (!opts.skipStepGuard && !validateCurrentStep()) return;

  formError.hidden = true;
  inputPanel.hidden = true;
  stepProgress.hidden = true;
  resultPanel.hidden = true;
  if (comingSoon) comingSoon.hidden = true;
  loadingPanel.hidden = false;

  const started = performance.now();
  const parameters = readParameters(form);
  lastParameters = parameters;
  // New evaluate → drop previous what-if cache (expert toggle still keeps mid-session).
  clearCompetitionSimCache();

  try {
    const response = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parameters }),
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    const wait = Math.max(0, 280 - (performance.now() - started));
    await new Promise((r) => setTimeout(r, wait));
    loadingPanel.hidden = true;
    if (!response.ok) {
      applyEvaluateErrorUi(
        formatApiError(
          payload?.detail ?? payload,
          `요청 실패 (HTTP ${response.status})`,
        ),
      );
      return;
    }
    renderResult(payload);
  } catch (error) {
    loadingPanel.hidden = true;
    applyEvaluateErrorUi(
      error instanceof TypeError
        ? "네트워크 오류로 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
        : formatApiError(null, String(error)),
    );
  }
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runEvaluate();
});

buildForm().catch((err) => {
  formError.hidden = false;
  formError.textContent = `템플릿 로드 실패: ${err}`;
  form.hidden = false;
  wizardNav.hidden = true;
});
