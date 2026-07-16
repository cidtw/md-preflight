#!/usr/bin/env node
/**
 * Smoke: report_export markdown/csv builders.
 * Run: node scripts/verify_report_export.mjs
 */
import {
  buildComparisonCsv,
  buildMarkdown,
  reportBasename,
} from "../app/web/report_export.mjs";

const sample = {
  template_id: "rop-adjust-v1",
  template_version: "1.3.1",
  recommendation: "재고 30개 이하에서 발주하세요.",
  recommendation_technical: "ROP 30 · SS 6 · Q 28",
  guidance: ["규모 기준 적용"],
  summary: {
    product_name: "냉장 간편식",
    store_type_label: "편의점",
    store_size_label: "소형",
    avg_ticket_label: "8천 이하",
    location_dong: "서울시 마포구 서교동",
    trade_area_label: "오피스",
    accessibility_label: "건물 내",
    service_level_label: "95%",
    order_day_pattern_label: "월·수·금",
    use_precise_location: false,
    store_address: null,
  },
  comparison: {
    rows: [
      {
        metric: "발주 시점 재고",
        standard_value: 15,
        recommended_value: 30,
        delta: 15,
        unit: "개",
        delta_label: "▲ 15 상향",
      },
    ],
    rop_guidance: "재고 30개 이하에서 발주",
  },
  comparison_technical: {
    rows: [
      {
        metric: "ROP",
        standard_value: 15,
        recommended_value: 30,
        delta: 15,
        unit: "개",
        delta_label: "▲ 15",
      },
    ],
    rop_guidance: "ROP=30",
  },
  evidence: [
    {
      id: "lt_access",
      title: "배송",
      calc_summary: "핵심: 여유 +6",
      points: ["건물 내 입지"],
    },
  ],
  evidence_technical: [
    {
      id: "lt_access",
      title: "LT buffer",
      calc_summary: "buffer=6",
      points: ["Z=1.65"],
    },
  ],
  calc: {
    recommended_rop: 30,
    store_safety_stock: 6,
    suggested_order_qty: 28,
    order_days_label: "월·수·금",
    order_cycle_days: 2.33,
    standard_lead_time_days: 2,
  },
};

let failed = 0;
function assert(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error(`FAIL: ${msg}`);
  } else {
    console.log(`ok  — ${msg}`);
  }
}

const md = buildMarkdown(sample, { expert: false });
assert(md.includes("# 매장 특화 ROP 리포트"), "md has title");
assert(md.includes("냉장 간편식"), "md has product");
assert(md.includes("쉬운 설명"), "md plain mode label");
assert(md.includes("발주 시점 재고"), "md has comparison metric");

const mdTech = buildMarkdown(sample, { expert: true });
assert(mdTech.includes("전문 해설"), "md technical mode");
assert(mdTech.includes("ROP 30"), "md uses technical recommendation");

const csv = buildComparisonCsv(sample, { expert: false });
assert(csv.startsWith("\uFEFF"), "csv has BOM");
assert(csv.includes("metric,standard"), "csv header");
assert(csv.includes("발주 시점 재고"), "csv row");

const base = reportBasename(sample);
assert(base.startsWith("rop-report-"), "basename prefix");

if (failed) {
  console.error(`\n${failed} failed`);
  process.exit(1);
}
console.log("\nall report_export smoke checks passed");
