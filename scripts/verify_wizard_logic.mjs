#!/usr/bin/env node
/**
 * Smoke tests for app/web/wizard_logic.mjs
 * Run: node scripts/verify_wizard_logic.mjs
 */
import {
  PRECISE_ADDRESS_REQUIRED_MSG,
  evaluateErrorUiState,
  formatApiError,
  isStoreAddressRequired,
  restoreStepIndexAfterEvaluateError,
  sanitizeEvaluateParameters,
  validateStoreAddress,
} from "../app/web/wizard_logic.mjs";

let failed = 0;

function assert(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error(`FAIL: ${msg}`);
  } else {
    console.log(`ok  — ${msg}`);
  }
}

// --- precise-address gating ---
assert(!isStoreAddressRequired(false), "address not required when precise off");
assert(isStoreAddressRequired(true), "address required when precise on");

assert(validateStoreAddress(false, "").ok, "skip empty address when precise off");
assert(validateStoreAddress(false, "   ").ok, "skip whitespace when precise off");

const miss = validateStoreAddress(true, "");
assert(!miss.ok, "fail empty address when precise on");
assert(
  miss.message === PRECISE_ADDRESS_REQUIRED_MSG,
  "empty-address message is user-facing Korean",
);
assert(miss.focusKey === "store_address", "focus store_address on fail");

assert(!validateStoreAddress(true, "   ").ok, "whitespace-only address fails");
assert(validateStoreAddress(true, "서울시 마포구 양화로 123").ok, "real address passes");

// --- payload sanitize ---
const stripped = sanitizeEvaluateParameters({
  use_precise_location: false,
  store_address: "should-drop",
  product_name: "X",
});
assert(stripped.use_precise_location === false, "precise flag false");
assert(!("store_address" in stripped), "strip store_address when precise off");
assert(stripped.product_name === "X", "other fields kept");

const kept = sanitizeEvaluateParameters({
  use_precise_location: true,
  store_address: "서울 마포",
});
assert(kept.store_address === "서울 마포", "keep address when precise on");

// --- loading → error restore last step ---
// STEPS = welcome, basic, detail, inventory → length 4, last index 3
assert(
  restoreStepIndexAfterEvaluateError(4) === 3,
  "restore to inventory step (last input)",
);
assert(restoreStepIndexAfterEvaluateError(1) === 0, "single-step edge");
assert(restoreStepIndexAfterEvaluateError(0) === 0, "empty steps edge");

const ui = evaluateErrorUiState();
assert(ui.loadingHidden === true, "loading panel hidden after error");
assert(ui.inputHidden === false, "input panel shown after error");
assert(ui.stepProgressHidden === false, "step progress shown after error");
assert(ui.formErrorHidden === false, "form error visible after error");

// --- error message formatting ---
assert(formatApiError("직접 메시지", "fb") === "직접 메시지", "string detail");
assert(
  formatApiError([{ loc: ["body", "x"], msg: "bad" }], "fb") === "body.x: bad",
  "array validation detail",
);
assert(formatApiError(null, "fallback") === "fallback", "null → fallback");

if (failed > 0) {
  console.error(`\n${failed} assertion(s) failed`);
  process.exit(1);
}
console.log("\nall wizard_logic smoke checks passed");
