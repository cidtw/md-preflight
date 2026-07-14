const form = document.getElementById("eval-form");
const inputPanel = document.getElementById("input-panel");
const loadingPanel = document.getElementById("loading-panel");
const resultPanel = document.getElementById("result-panel");
const formError = document.getElementById("form-error");
const submitBtn = document.getElementById("submit-btn");

const DEFAULTS = {
  product_name: "냉장 간편식",
  store_type: "convenience",
  store_size: "cv_s",
  avg_ticket: "t_le_8k",
  location_dong: "서울시 마포구 서교동",
  trade_area: "office",
  accessibility: "indoor",
  daily_demand: 12,
  standard_lead_time_days: 2,
  standard_rop: 15,
};

function fieldControl(spec) {
  if (spec.options && spec.options.length) {
    const select = document.createElement("select");
    select.name = spec.key;
    select.required = spec.required;
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
  input.required = spec.required;
  if (spec.type === "number") {
    input.type = "number";
    input.step = "any";
    if (spec.minimum != null) input.min = String(spec.minimum);
    if (spec.maximum != null) input.max = String(spec.maximum);
  } else {
    input.type = "text";
  }
  if (DEFAULTS[spec.key] != null) input.value = String(DEFAULTS[spec.key]);
  if (spec.description) input.placeholder = spec.description;
  return input;
}

async function buildForm() {
  const res = await fetch("/api/template");
  const template = await res.json();
  form.innerHTML = "";
  for (const spec of template.parameters) {
    const label = document.createElement("label");
    label.textContent = spec.label + (spec.required ? "" : " (선택)");
    if (spec.description) {
      const hint = document.createElement("small");
      hint.textContent = spec.description;
      hint.style.opacity = "0.75";
      label.appendChild(document.createElement("br"));
      label.appendChild(hint);
    }
    label.appendChild(fieldControl(spec));
    form.appendChild(label);
  }
}

function readParameters(formEl) {
  const data = new FormData(formEl);
  const parameters = {};
  for (const [key, raw] of data.entries()) {
    if (raw === "" || raw == null) continue;
    const asNum = Number(raw);
    if (raw !== "" && !Number.isNaN(asNum) && String(raw).trim() !== "" && /^-?\d/.test(String(raw))) {
      // numeric fields from number inputs
      const input = formEl.elements.namedItem(key);
      if (input && input.type === "number") {
        parameters[key] = asNum;
        continue;
      }
    }
    parameters[key] = String(raw);
  }
  return parameters;
}

function fmt(n, digits = 1) {
  return Number(n).toLocaleString("ko-KR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });
}

function renderResult(payload) {
  const guideHtml =
    payload.guidance && payload.guidance.length
      ? `<div class="guidance"><strong>입력 안내</strong><ul>${payload.guidance
          .map((g) => `<li>${escapeHtml(g)}</li>`)
          .join("")}</ul></div>`
      : "";

  const s = payload.summary;
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
      <h2>3. 추천 결과</h2>
      <p class="hero-rec">${escapeHtml(payload.recommendation)}</p>
      ${guideHtml}
      <h3>매장·품목 요약</h3>
      <dl class="summary-grid">
        <dt>분석 품목</dt><dd>${escapeHtml(s.product_name)}</dd>
        <dt>유형 / 규모</dt><dd>${escapeHtml(s.store_type_label)} / ${escapeHtml(s.store_size_label)}</dd>
        <dt>객단가</dt><dd>${escapeHtml(s.avg_ticket_label)}</dd>
        <dt>입지 / 접근성</dt><dd>${escapeHtml(s.location_dong)} / ${escapeHtml(s.accessibility_label)}</dd>
        <dt>상권</dt><dd>${escapeHtml(s.trade_area_label)}</dd>
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
      <h2 style="margin:1.1rem 0 0;font-size:1.05rem">계산 근거 · 지식 베이스</h2>
      ${evidence}
    </section>
    <div class="actions">
      <button type="button" class="secondary" id="again-btn">다시 입력</button>
    </div>
  `;
  resultPanel.hidden = false;
  document.getElementById("again-btn")?.addEventListener("click", () => {
    resultPanel.hidden = true;
    inputPanel.hidden = false;
    submitBtn.hidden = false;
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.hidden = true;
  inputPanel.hidden = true;
  submitBtn.hidden = true;
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
    const payload = await response.json();
    // Keep the loading beat short so internal calc feels like a direct 1→3 flow.
    const wait = Math.max(0, 280 - (performance.now() - started));
    await new Promise((r) => setTimeout(r, wait));
    loadingPanel.hidden = true;
    if (!response.ok) {
      inputPanel.hidden = false;
      submitBtn.hidden = false;
      formError.hidden = false;
      formError.textContent = payload.detail || JSON.stringify(payload);
      return;
    }
    renderResult(payload);
  } catch (error) {
    loadingPanel.hidden = true;
    inputPanel.hidden = false;
    submitBtn.hidden = false;
    formError.hidden = false;
    formError.textContent = String(error);
  }
});

buildForm().catch((err) => {
  formError.hidden = false;
  formError.textContent = `템플릿 로드 실패: ${err}`;
});
