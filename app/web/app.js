import {
  evaluateErrorUiState,
  formatApiError,
  restoreStepIndexAfterEvaluateError,
  sanitizeEvaluateParameters,
  validateStoreAddress,
} from "./wizard_logic.mjs";

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
  if (spec.description) {
    const hint = document.createElement("small");
    hint.className = "field-hint";
    hint.textContent = spec.description;
    label.appendChild(hint);
  }
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
  btnNext.hidden = isLast || isWelcome;
  submitBtn.hidden = !isLast;

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

function renderResult(payload) {
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

  const rows = payload.comparison.rows
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

  const evidence = payload.evidence
    .map(
      (block) => `<article class="card evidence">
        <h3>${escapeHtml(block.title)}</h3>
        <p class="calc">${escapeHtml(block.calc_summary)}</p>
        <ul>${block.points.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul>
      </article>`,
    )
    .join("");

  resultPanel.innerHTML = `
    <section class="card">
      <h2>추천 결과</h2>
      <p class="hero-rec">${escapeHtml(payload.recommendation)}</p>
      ${guideHtml}
      <h3>매장·품목 요약</h3>
      <dl class="summary-grid">
        <dt>분석 품목</dt><dd>${escapeHtml(s.product_name)}</dd>
        <dt>유형 / 규모</dt><dd>${escapeHtml(s.store_type_label)} / ${escapeHtml(s.store_size_label)}</dd>
        <dt>객단가</dt><dd>${escapeHtml(s.avg_ticket_label)}</dd>
        <dt>입지 / 접근성</dt><dd>${escapeHtml(s.location_dong)} / ${escapeHtml(s.accessibility_label)}</dd>
        ${addressRow}
        <dt>상권</dt><dd>${escapeHtml(s.trade_area_label)}</dd>
        <dt>서비스 레벨</dt><dd>${escapeHtml(s.service_level_label || "-")}</dd>
        <dt>발주 요일 패턴</dt><dd>${escapeHtml(s.order_day_pattern_label || "-")}</dd>
      </dl>
    </section>
    <section class="card">
      <h2>ROP 비교 대시보드</h2>
      <table class="cmp">
        <thead>
          <tr><th>구분</th><th>업계/사내 표준</th><th>매장 맞춤 추천</th><th>변동</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="rop-guide">${escapeHtml(payload.comparison.rop_guidance)}</p>
    </section>
    <section>
      <h2 class="section-heading">계산 근거 · 지식 베이스</h2>
      ${evidence}
    </section>
    <div class="actions">
      <button type="button" class="btn-secondary" id="again-btn">처음부터 다시</button>
    </div>
  `;
  resultPanel.hidden = false;
  document.getElementById("again-btn")?.addEventListener("click", () => {
    resultPanel.hidden = true;
    inputPanel.hidden = false;
    showStep(0);
  });
}

document.getElementById("welcome-start")?.addEventListener("click", () => {
  showStep(1);
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
  if (!validateCurrentStep()) return;

  formError.hidden = true;
  inputPanel.hidden = true;
  stepProgress.hidden = true;
  resultPanel.hidden = true;
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
    if (!response.ok) {
      applyEvaluateErrorUi(
        formatApiError(
          payload?.detail ?? payload,
          `요청 실패 (HTTP ${response.status})`,
        ),
      );
      return;
    }
    loadingPanel.hidden = true;
    renderResult(payload);
  } catch (error) {
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
