import {
  evaluateErrorUiState,
  formatApiError,
  restoreStepIndexAfterEvaluateError,
  sanitizeEvaluateParameters,
  validateStoreAddress,
} from "./wizard_logic.mjs";
import { initTheme } from "./theme.mjs";
import { exportReport } from "./report_export.mjs";

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

/** @type {object | null} */
let lastPayload = null;

/** @type {Record<string, object>} */
let specsByKey = {};

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
  const addressLabel = form?.querySelector('label[data-field-key="store_address"]');
  const addressInput = form?.elements.namedItem("store_address");
  const on = Boolean(checkbox && "checked" in checkbox && checkbox.checked);
  if (addressLabel) addressLabel.hidden = !on;
  if (addressInput && "required" in addressInput) {
    addressInput.required = on;
    if (!on && "value" in addressInput) addressInput.value = "";
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
  showStep(0);
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

  const data = new FormData(formEl);
  for (const [key, raw] of data.entries()) {
    if (key === "use_precise_location") continue;
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

  const s = payload.summary;
  const addressRow =
    s.use_precise_location && s.store_address
      ? `<dt>상세 주소</dt><dd>${escapeHtml(s.store_address)}</dd>`
      : "";

  const colStd = expert ? "표준" : "일반 기준";
  const colRec = expert ? "매장 맞춤" : "이 매장 추천";
  const colDelta = expert ? "Δ / 메모" : "어떻게 달라졌나";
  const evidenceTitle = expert
    ? "계산 근거 · 지식 베이스"
    : "왜 이렇게 나왔나요?";
  const cmpTitle = expert ? "ROP 비교" : "한눈에 보는 발주 기준";

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
        <div class="stat-value">${fmt(ropRow?.recommended_value ?? payload.calc.recommended_rop, 0)}</div>
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
      <div class="evidence-grid">${evidenceHtml}</div>
    </section>
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
  // Export menu is bound once (not on every renderResult) to avoid stacking
  // document click/keydown listeners when expert mode is toggled.
}

/** @type {boolean} */
let exportMenuBound = false;

function bindExportMenu() {
  if (exportMenuBound) return;
  const menu = document.getElementById("export-menu");
  const btn = document.getElementById("export-btn");
  const dropdown = document.getElementById("export-dropdown");
  if (!menu || !btn || !dropdown) return;
  exportMenuBound = true;

  const close = () => {
    dropdown.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  };
  const open = () => {
    dropdown.hidden = false;
    btn.setAttribute("aria-expanded", "true");
  };

  btn.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (dropdown.hidden) open();
    else close();
  });

  dropdown.querySelectorAll("[data-export]").forEach((item) => {
    item.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      const format = item.getAttribute("data-export");
      if (!lastPayload || !format) {
        close();
        return;
      }
      // Call export while still in the user-gesture stack (before close/DOM churn).
      const expertOn = document.getElementById("expert-mode")?.checked ?? readExpertMode();
      try {
        exportReport(format, lastPayload, { expert: expertOn });
      } catch (err) {
        window.alert(err instanceof Error ? err.message : String(err));
      } finally {
        close();
      }
    });
  });

  // Permanent outside-click / Escape handlers (single bind for page lifetime).
  document.addEventListener("click", (ev) => {
    if (dropdown.hidden) return;
    if (!menu.contains(ev.target)) close();
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !dropdown.hidden) close();
  });
}

// Export controls live in the result panel chrome; bind once at load.
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

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  // Guard: only inventory step may run evaluate (button can be forced via Enter).
  if (stepIndex !== STEPS.length - 1) {
    if (!validateCurrentStep()) return;
    if (stepIndex < STEPS.length - 1) showStep(stepIndex + 1);
    return;
  }
  if (!validateCurrentStep()) return;

  formError.hidden = true;
  inputPanel.hidden = true;
  stepProgress.hidden = true;
  resultPanel.hidden = true;
  if (comingSoon) comingSoon.hidden = true;
  loadingPanel.hidden = false;

  const started = performance.now();
  const parameters = readParameters(form);

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
});

buildForm().catch((err) => {
  formError.hidden = false;
  formError.textContent = `템플릿 로드 실패: ${err}`;
  form.hidden = false;
  wizardNav.hidden = true;
});
