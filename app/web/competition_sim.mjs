/**
 * Competition what-if simulation UI (calls POST /api/simulate).
 */

const SCENARIOS = [
  {
    id: "own_service_up",
    title: "내 매장 서비스·ROP 강화",
    blurb: "품절 방어를 올려 수요를 되찾는 경우",
  },
  {
    id: "competitor_pressure",
    title: "경쟁 매장 공세",
    blurb: "경쟁이 재고·판촉을 강화해 수요가 이탈",
  },
  {
    id: "own_lt_stress",
    title: "내 매장 LT 스트레스",
    blurb: "공급 리드타임이 늘어 부담·이탈 증가",
  },
  {
    id: "own_demand_rebound",
    title: "수요 반등",
    blurb: "입지·운영 개선으로 소진량이 늘어날 때",
  },
];

/**
 * @param {HTMLElement} container
 * @param {object} baseParameters last evaluate parameters
 * @param {{ expert?: boolean }} [opts]
 */
export function mountCompetitionSim(container, baseParameters, opts = {}) {
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

  const intensityLabel = document.createElement("label");
  intensityLabel.className = "sim-intensity";
  intensityLabel.innerHTML = `
    <span class="field-title">충격 강도 <em id="sim-intensity-val">50%</em></span>
    <input type="range" id="sim-intensity" min="0" max="100" value="50" />
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

  let selected = "own_service_up";
  const range = intensityLabel.querySelector("#sim-intensity");
  const rangeVal = intensityLabel.querySelector("#sim-intensity-val");

  const markSelected = () => {
    for (const btn of scenarioWrap.querySelectorAll(".sim-scenario-btn")) {
      btn.classList.toggle("is-active", btn.dataset.scenario === selected);
    }
  };
  markSelected();

  scenarioWrap.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-scenario]");
    if (!btn) return;
    selected = btn.getAttribute("data-scenario") || selected;
    markSelected();
  });

  range?.addEventListener("input", () => {
    if (rangeVal && range) rangeVal.textContent = `${range.value}%`;
  });

  runBtn.addEventListener("click", async () => {
    runBtn.disabled = true;
    result.hidden = false;
    result.innerHTML = `<p class="mute">시뮬레이션 계산 중…</p>`;
    const intensity = Number(range?.value || 50) / 100;
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
          data.detail || `HTTP ${res.status}`,
        )}</p>`;
        return;
      }
      result.innerHTML = renderSimResult(data, Boolean(opts.expert));
    } catch (err) {
      result.innerHTML = `<p class="form-error">${escapeHtml(String(err))}</p>`;
    } finally {
      runBtn.disabled = false;
    }
  });
}

function renderSimResult(data, expert) {
  const b = data.baseline;
  const s = data.shocked;
  const delta = data.own_sales_index_delta_pct;
  const deltaCls = delta > 0 ? "delta-up" : delta < 0 ? "delta-down" : "";
  const summary = expert ? data.technical_summary : data.plain_summary;
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
        <tbody>
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
            <td>여유 재고 SS (개)</td>
            <td>${fmt(b.store_safety_stock)}</td>
            <td><strong>${fmt(s.store_safety_stock)}</strong></td>
          </tr>
          <tr>
            <td>1회 발주량 Q (개)</td>
            <td>${fmt(b.suggested_order_qty)}</td>
            <td><strong>${fmt(s.suggested_order_qty)}</strong></td>
          </tr>
          <tr>
            <td>LT (일)</td>
            <td>${fmt(b.standard_lead_time_days)}</td>
            <td><strong>${fmt(s.standard_lead_time_days)}</strong></td>
          </tr>
          <tr>
            <td>경쟁 수요 계수</td>
            <td>${fmt(b.competition_demand_factor, 3)}</td>
            <td><strong>${fmt(s.competition_demand_factor, 3)}</strong></td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="sim-sales-delta ${deltaCls}">
      매출(유효 수요) 지수 변화: <strong>${delta > 0 ? "+" : ""}${fmt(delta, 1)}%</strong>
    </p>
  `;
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
