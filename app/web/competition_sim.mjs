/**
 * Competition what-if simulation UI (calls POST /api/simulate).
 * Last successful result is cached so expert/plain toggle does not require re-run.
 */

const SCENARIOS = [
  {
    id: "own_service_up",
    title: "내 매장 서비스·ROP 강화",
    blurb: "품절 방어를 올려 수요를 되찾는 경우",
    intensityHelp: {
      low: "약함: 서비스 레벨·재고를 조금 올립니다.",
      high: "강함: 서비스 99%·수요 회복을 크게 가정합니다.",
      meaning:
        "슬라이더↑ → 내 매장 방어력·유효 수요↑, ROP·SS·Q도 함께 올라가는 경향",
    },
  },
  {
    id: "competitor_pressure",
    title: "경쟁 매장 공세",
    blurb: "경쟁이 재고·판촉을 강화해 수요가 이탈",
    intensityHelp: {
      low: "약함: 경쟁 영향이 작아 수요 이탈이 적습니다.",
      high: "강함: 경쟁이 세져 내 매장 유효 수요가 크게 줄 수 있습니다.",
      meaning:
        "슬라이더↑ → 일 소진 수요 이탈(최대 약 −28%) · 경쟁 스캔 계수와 별개 충격, 발주량·ROP 재조정",
    },
  },
  {
    id: "own_lt_stress",
    title: "내 매장 LT 스트레스",
    blurb: "공급 리드타임이 늘어 부담·이탈 증가",
    intensityHelp: {
      low: "약함: 리드타임이 조금 늘어납니다.",
      high: "강함: LT가 크게 늘고 품절 리스크로 수요도 일부 이탈합니다.",
      meaning: "슬라이더↑ → LT·여유재고(SS)·ROP↑, 유효 수요는 소폭↓",
    },
  },
  {
    id: "own_demand_rebound",
    title: "수요 반등",
    blurb: "입지·운영 개선으로 소진량이 늘어날 때",
    intensityHelp: {
      low: "약함: 일 소진량이 소폭 증가합니다.",
      high: "강함: 소진량이 크게 늘어 ROP·발주량도 커집니다.",
      meaning: "슬라이더↑ → 일 소진·ROP·Q↑ (낙관 시나리오)",
    },
  },
];

/** @type {{ data: object, scenario: string, intensityPct: number } | null} */
let lastSimState = null;

/**
 * @param {HTMLElement} container
 * @param {object} baseParameters last evaluate parameters
 * @param {{ expert?: boolean }} [opts]
 */
export function mountCompetitionSim(container, baseParameters, opts = {}) {
  const expert = Boolean(opts.expert);
  container.innerHTML = "";
  container.className = "sim-panel";

  const head = document.createElement("div");
  head.className = "sim-head";
  head.innerHTML = `
    <h2 class="section-title">경쟁 매장 시뮬레이션</h2>
    <p class="lede sim-lede">
      LT·ROP·수요 충격을 가정해 내 매장 지표 변화와 경쟁 대응 해석을 시연합니다.
      (결정론 근사 · 실측 시장점유율 아님)
    </p>
  `;

  const controls = document.createElement("div");
  controls.className = "sim-controls";

  const scenarioWrap = document.createElement("div");
  scenarioWrap.className = "sim-scenarios";
  for (const s of SCENARIOS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "sim-scenario-btn";
    btn.dataset.scenario = s.id;
    btn.innerHTML = `<strong>${escapeHtml(s.title)}</strong><span>${escapeHtml(s.blurb)}</span>`;
    scenarioWrap.appendChild(btn);
  }

  const initialPct = lastSimState?.intensityPct ?? 50;
  const initialScenario = lastSimState?.scenario ?? "own_service_up";

  const intensityLabel = document.createElement("label");
  intensityLabel.className = "sim-intensity";
  intensityLabel.innerHTML = `
    <span class="field-title">충격 강도 <em id="sim-intensity-val">${initialPct}%</em></span>
    <input type="range" id="sim-intensity" min="0" max="100" value="${initialPct}" />
    <p class="sim-intensity-help" id="sim-intensity-help"></p>
  `;

  const runBtn = document.createElement("button");
  runBtn.type = "button";
  runBtn.className = "btn btn-primary";
  runBtn.id = "sim-run";
  runBtn.textContent = "시나리오 실행";

  const result = document.createElement("div");
  result.className = "sim-result";
  result.hidden = true;

  controls.appendChild(scenarioWrap);
  controls.appendChild(intensityLabel);
  controls.appendChild(runBtn);
  container.appendChild(head);
  container.appendChild(controls);
  container.appendChild(result);

  let selected = initialScenario;
  const range = intensityLabel.querySelector("#sim-intensity");
  const rangeVal = intensityLabel.querySelector("#sim-intensity-val");
  const helpEl = intensityLabel.querySelector("#sim-intensity-help");

  const markSelected = () => {
    for (const btn of scenarioWrap.querySelectorAll(".sim-scenario-btn")) {
      btn.classList.toggle("is-active", btn.dataset.scenario === selected);
    }
  };

  const updateIntensityHelp = () => {
    const meta = SCENARIOS.find((s) => s.id === selected);
    const pct = Number(range?.value || 50);
    if (!helpEl || !meta) return;
    const side =
      pct < 35 ? meta.intensityHelp.low : pct > 65 ? meta.intensityHelp.high : null;
    const mid =
      "중간: 보통 수준의 충격입니다. 좌(약함) ↔ 우(강함)로 세기를 조절하세요.";
    helpEl.innerHTML = `
      <span class="sim-help-main">${escapeHtml(meta.intensityHelp.meaning)}</span>
      <span class="sim-help-side">${escapeHtml(side || mid)}</span>
    `;
  };

  markSelected();
  updateIntensityHelp();

  // Restore previous result when expert toggle re-mounts this panel.
  if (lastSimState?.data) {
    result.hidden = false;
    result.innerHTML = renderSimResult(lastSimState.data, expert);
  }

  scenarioWrap.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-scenario]");
    if (!btn) return;
    selected = btn.getAttribute("data-scenario") || selected;
    markSelected();
    updateIntensityHelp();
  });

  range?.addEventListener("input", () => {
    if (rangeVal && range) rangeVal.textContent = `${range.value}%`;
    updateIntensityHelp();
  });

  runBtn.addEventListener("click", async () => {
    runBtn.disabled = true;
    result.hidden = false;
    result.innerHTML = `<p class="mute">시뮬레이션 계산 중…</p>`;
    const intensityPct = Number(range?.value || 50);
    const intensity = intensityPct / 100;
    try {
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parameters: baseParameters,
          scenario: selected,
          intensity,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        result.innerHTML = `<p class="form-error">${escapeHtml(
          typeof data.detail === "string"
            ? data.detail
            : `요청 실패 (HTTP ${res.status})`,
        )}</p>`;
        return;
      }
      lastSimState = { data, scenario: selected, intensityPct };
      result.innerHTML = renderSimResult(data, expert);
    } catch (err) {
      result.innerHTML = `<p class="form-error">${escapeHtml(String(err))}</p>`;
    } finally {
      runBtn.disabled = false;
    }
  });
}

/** Clear cached sim when starting a new evaluate run. */
export function clearCompetitionSimCache() {
  lastSimState = null;
}

/**
 * Render simulation API payload to HTML (exported for smoke tests).
 * @param {object} data
 * @param {boolean} expert
 * @returns {string}
 */
export function renderSimResult(data, expert) {
  const b = data.baseline;
  const s = data.shocked;
  const delta = data.own_sales_index_delta_pct;
  const deltaCls = delta > 0 ? "delta-up" : delta < 0 ? "delta-down" : "";
  const summary = expert
    ? data.technical_summary || data.plain_summary
    : data.plain_summary;
  const tableRows = expert
    ? `
          <tr>
            <td>유효 일 소진 D<sub>eff</sub> (개)</td>
            <td>${fmt(b.effective_daily_demand)}</td>
            <td><strong>${fmt(s.effective_daily_demand)}</strong></td>
          </tr>
          <tr>
            <td>재발주점 ROP (개)</td>
            <td>${fmt(b.recommended_rop, 0)}</td>
            <td><strong>${fmt(s.recommended_rop, 0)}</strong></td>
          </tr>
          <tr>
            <td>안전재고 SS (개)</td>
            <td>${fmt(b.store_safety_stock)}</td>
            <td><strong>${fmt(s.store_safety_stock)}</strong></td>
          </tr>
          <tr>
            <td>1회 발주량 Q (개)</td>
            <td>${fmt(b.suggested_order_qty)}</td>
            <td><strong>${fmt(s.suggested_order_qty)}</strong></td>
          </tr>
          <tr>
            <td>리드타임 LT (일)</td>
            <td>${fmt(b.standard_lead_time_days)}</td>
            <td><strong>${fmt(s.standard_lead_time_days)}</strong></td>
          </tr>
          <tr>
            <td>경쟁 수요 계수 (1=무분산)</td>
            <td>${fmt(b.competition_demand_factor, 3)}</td>
            <td><strong>${fmt(s.competition_demand_factor, 3)}</strong></td>
          </tr>
          <tr>
            <td>경쟁 강도 지수</td>
            <td>${fmt(b.competition_intensity, 3)}</td>
            <td><strong>${fmt(s.competition_intensity, 3)}</strong></td>
          </tr>`
    : `
          <tr>
            <td>유효 일 소진 (개)</td>
            <td>${fmt(b.effective_daily_demand)}</td>
            <td><strong>${fmt(s.effective_daily_demand)}</strong></td>
          </tr>
          <tr>
            <td>추천 ROP (개)</td>
            <td>${fmt(b.recommended_rop, 0)}</td>
            <td><strong>${fmt(s.recommended_rop, 0)}</strong></td>
          </tr>
          <tr>
            <td>여유 재고 (개)</td>
            <td>${fmt(b.store_safety_stock)}</td>
            <td><strong>${fmt(s.store_safety_stock)}</strong></td>
          </tr>
          <tr>
            <td>1회 발주량 (개)</td>
            <td>${fmt(b.suggested_order_qty)}</td>
            <td><strong>${fmt(s.suggested_order_qty)}</strong></td>
          </tr>
          <tr>
            <td>배송 리드타임 (일)</td>
            <td>${fmt(b.standard_lead_time_days)}</td>
            <td><strong>${fmt(s.standard_lead_time_days)}</strong></td>
          </tr>
          <tr>
            <td>경쟁으로 줄어든 수요 비율 보정</td>
            <td>${fmt(b.competition_demand_factor, 3)}</td>
            <td><strong>${fmt(s.competition_demand_factor, 3)}</strong></td>
          </tr>`;

  const advicePanel = renderDeclineAdvicePanel(data);

  return `
    <div class="verdict sim-verdict">${escapeHtml(summary)}</div>
    <p class="sim-competitor">${escapeHtml(data.competitor_response_note)}</p>
    <div class="sim-compare table-wrap">
      <table class="cmp">
        <thead>
          <tr>
            <th>지표</th>
            <th>현재</th>
            <th>시나리오</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>
    <p class="sim-sales-delta ${deltaCls}">
      매출(유효 수요) 지수 변화: <strong>${delta > 0 ? "+" : ""}${fmt(delta, 1)}%</strong>
    </p>
    ${advicePanel}
  `;
}

/**
 * Sales-decline AI / fallback advice panel (API fields → UI).
 * @param {object} data
 * @returns {string}
 */
export function renderDeclineAdvicePanel(data) {
  if (!data?.sales_decline || !data?.ai_advice) return "";
  const badge = data.ai_used
    ? `<span class="sim-ai-badge is-ai">AI 맞춤</span>`
    : `<span class="sim-ai-badge is-fallback">로컬 폴백</span>`;
  const note = data.ai_note
    ? `<p class="sim-ai-note mute">${escapeHtml(data.ai_note)}</p>`
    : "";
  return `
    <section class="sim-ai-panel" data-testid="sim-decline-advice">
      <header class="sim-ai-head">
        <h3 class="sim-ai-title">매출 하락 대응 방안</h3>
        ${badge}
      </header>
      ${note}
      <div class="sim-ai-body">${lightMarkdownToHtml(data.ai_advice)}</div>
    </section>
  `;
}

/** Minimal safe markdown → HTML for advice (bold, headings, lists, breaks). */
function lightMarkdownToHtml(md) {
  const lines = String(md || "").split("\n");
  const out = [];
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      out.push("<br/>");
      continue;
    }
    if (/^###\s+/.test(line)) {
      out.push(`<h4 class="sim-ai-h">${inlineMd(line.replace(/^###\s+/, ""))}</h4>`);
      continue;
    }
    if (/^>\s?/.test(line)) {
      out.push(`<p class="sim-ai-quote">${inlineMd(line.replace(/^>\s?/, ""))}</p>`);
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      out.push(`<div class="sim-ai-li">• ${inlineMd(line.replace(/^[-*]\s+/, ""))}</div>`);
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      out.push(`<div class="sim-ai-li">${inlineMd(line)}</div>`);
      continue;
    }
    out.push(`<p class="sim-ai-p">${inlineMd(line)}</p>`);
  }
  return out.join("\n");
}

function inlineMd(text) {
  // Escape first, then restore simple **bold** markers.
  const esc = escapeHtml(text);
  return esc.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
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
