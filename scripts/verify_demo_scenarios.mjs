/**
 * Node smoke for demo_scenarios.mjs (no DOM).
 * Run: node scripts/verify_demo_scenarios.mjs
 */
import {
  DEMO_SCENARIOS,
  VERIFIED_DEMO_STORES,
  getDemoScenario,
  getVerifiedDemoStore,
  listDemoScenarioIds,
  listVerifiedDemoStoreIds,
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

assert(VERIFIED_DEMO_STORES.length >= 1 && VERIFIED_DEMO_STORES.length <= 2, "1–2 verified stores");
assert(DEMO_SCENARIOS.length >= 3, "at least 3 explore scenarios");
assert(
  new Set(listDemoScenarioIds()).size === listDemoScenarioIds().length,
  "unique ids across verified+explore",
);
assert(listVerifiedDemoStoreIds().length === VERIFIED_DEMO_STORES.length, "verified id list");

for (const s of [...VERIFIED_DEMO_STORES, ...DEMO_SCENARIOS]) {
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

for (const s of VERIFIED_DEMO_STORES) {
  assert(s.tier === "verified", `${s.id} tier verified`);
  assert(Boolean(s.storeLabel && s.verificationNote), `${s.id} store meta`);
  assert(s.parameters.use_precise_location === false, `${s.id} admin-dong path`);
  // Live evaluate should match expected within engine (checked in pytest)
  assert(s.expected && s.expected.recommended_rop != null, `${s.id} expected rop`);
}

assert(
  getVerifiedDemoStore("verified-a-yeoksam-cvs")?.parameters.daily_demand === 12,
  "verified A lookup",
);
assert(
  getDemoScenario("verified-b-yeoksam-super")?.parameters.store_type === "supermarket",
  "getDemoScenario finds verified",
);
assert(getDemoScenario("cv-capa-tight")?.parameters.store_type === "convenience", "lookup explore");
assert(getDemoScenario("missing") === undefined, "missing lookup");
assert(
  getDemoScenario("precise-event")?.parameters.consider_temp_foot_traffic === true,
  "event scenario",
);

if (!process.exitCode) {
  console.log("\nall demo_scenarios smoke checks passed");
}
