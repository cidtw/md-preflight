/**
 * Node smoke for demo_scenarios.mjs (no DOM).
 * Run: node scripts/verify_demo_scenarios.mjs
 */
import {
  DEMO_SCENARIOS,
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

assert(DEMO_SCENARIOS.length >= 3, "at least 3 scenarios");
assert(new Set(listDemoScenarioIds()).size === DEMO_SCENARIOS.length, "unique ids");

for (const s of DEMO_SCENARIOS) {
  assert(Boolean(s.id && s.title && s.blurb && s.highlight), `meta for ${s.id}`);
  assert(s.parameters && typeof s.parameters === "object", `params for ${s.id}`);
  for (const k of REQUIRED) {
    assert(s.parameters[k] !== undefined && s.parameters[k] !== "", `${s.id}.${k}`);
  }
  if (s.parameters.use_precise_location) {
    assert(
      String(s.parameters.store_address || "").trim().length > 0,
      `${s.id} precise requires address`,
    );
  }
}

assert(getDemoScenario("cv-capa-tight")?.parameters.store_type === "convenience", "lookup capa");
assert(getDemoScenario("missing") === undefined, "missing lookup");
assert(
  getDemoScenario("precise-event")?.parameters.consider_temp_foot_traffic === true,
  "event scenario",
);

if (!process.exitCode) {
  console.log("\nall demo_scenarios smoke checks passed");
}
