#!/usr/bin/env node
/**
 * Smoke tests for app/web/competition_sim.mjs render helpers.
 * Run: node scripts/verify_competition_sim.mjs
 */
import {
  renderDeclineAdvicePanel,
  renderSimResult,
} from "../app/web/competition_sim.mjs";

let failed = 0;

function assert(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error(`FAIL: ${msg}`);
  } else {
    console.log(`ok  — ${msg}`);
  }
}

const baseline = {
  daily_demand: 40,
  effective_daily_demand: 40,
  recommended_rop: 100,
  store_safety_stock: 20,
  suggested_order_qty: 80,
  standard_lead_time_days: 2,
  competition_demand_factor: 1,
  competition_intensity: 0,
};

const shocked = {
  ...baseline,
  daily_demand: 30,
  effective_daily_demand: 30,
  recommended_rop: 75,
  store_safety_stock: 15,
  suggested_order_qty: 60,
};

const fallbackPhrase = "로컬 폴백 · API 키 없음";
const adviceMd = [
  "### AI 대응 방안 (로컬 폴백 · API 키 없음 또는 호출 실패)",
  "",
  "유효 수요 지수 약 **-22.4%** 로 매출 하락이 예상됩니다.",
  "",
  "1. **SS·ROP**",
  "   - 안전재고: 20.0개 → 목표 **15.0개**",
].join("\n");

const declinePayload = {
  plain_summary: "경쟁 공세 시나리오 요약",
  technical_summary: "tech summary D_eff",
  competitor_response_note: "경쟁 대응 노트",
  own_sales_index_delta_pct: -22.4,
  sales_decline: true,
  ai_advice: adviceMd,
  ai_used: false,
  ai_note: "XAI_API_KEY 미설정 — 폴백 가이드 사용",
  baseline,
  shocked,
};

const noDecline = {
  ...declinePayload,
  own_sales_index_delta_pct: 5,
  sales_decline: false,
  ai_advice: null,
};

const html = renderSimResult(declinePayload, false);
assert(html.includes("sim-decline-advice") || html.includes("sim-ai-panel"), "panel class present");
assert(html.includes("매출 하락 대응 방안"), "panel title present");
assert(html.includes(fallbackPhrase) || html.includes("로컬 폴백"), "fallback badge/text visible");
assert(html.includes("XAI_API_KEY 미설정"), "ai_note surfaced");
assert(html.includes("SS·ROP") || html.includes("SS"), "advice body rendered");
assert(html.includes("-22.4") || html.includes("−22.4") || html.includes("22.4"), "delta shown");

const emptyPanel = renderDeclineAdvicePanel(noDecline);
assert(emptyPanel === "", "no panel when sales_decline false");

const missingAdvice = renderDeclineAdvicePanel({
  sales_decline: true,
  ai_advice: null,
});
assert(missingAdvice === "", "no panel without ai_advice");

const expert = renderSimResult(declinePayload, true);
assert(expert.includes("D") || expert.includes("유효"), "expert table still renders");

if (failed) {
  console.error(`\n${failed} failure(s)`);
  process.exit(1);
}
console.log("\nall competition_sim smoke tests passed");
