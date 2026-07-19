/**
 * Node smoke for demo_scenarios.mjs (no DOM).
 * Run: node scripts/verify_demo_scenarios.mjs
 */
import {
  DEMO_SCENARIOS,
  VERIFIED_DEMO_STORES,
  getDemoScenario,
  listDemoScenarioIds,
} from "../app/web/demo_scenarios.mjs";

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL —", msg);
    process.exitCode = 1;
    throw new Error(msg);
  }
  console.log("ok  —", msg);
}

const REQUIRED = [
  "product_name",
  "store_type",
  "store_size",
  "avg_ticket",
  "location_dong",
  "trade_area",
  "accessibility",
  "daily_demand",
];

// Live census is API-driven; client bundle may have 0 verified fallbacks.
assert(Array.isArray(VERIFIED_DEMO_STORES), "verified array");
assert(DEMO_SCENARIOS.length >= 2, "at least 2 explore scenarios");
assert(
  new Set(listDemoScenarioIds()).size === listDemoScenarioIds().length,
  "unique ids",
);

for (const s of DEMO_SCENARIOS) {
  assert(Boolean(s.id && s.title && s.blurb && s.highlight), `meta for ${s.id}`);
  assert(s.parameters && typeof s.parameters === "object", `params for ${s.id}`);
  for (const k of REQUIRED) {
    assert(s.parameters[k] !== undefined && s.parameters[k] !== "", `${s.id}.${k}`);
  }
}

assert(getDemoScenario("explore-anchor-precise")?.parameters.use_precise_location === true, "anchor precise");
assert(getDemoScenario("missing") === undefined, "missing lookup");

if (!process.exitCode) {
  console.log("\nall demo_scenarios smoke checks passed");
}
