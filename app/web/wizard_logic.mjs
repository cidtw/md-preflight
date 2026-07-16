/**
 * Pure wizard helpers for ROP multi-session form.
 * Kept free of DOM so Node smoke tests can cover gating rules without a browser.
 */

export const PRECISE_ADDRESS_REQUIRED_MSG =
  "정확한 위치 사용 시 매장 주소를 입력해 주세요.";

/**
 * When precise location is off, store_address is not required and is omitted from payload.
 * @param {boolean} preciseOn
 * @returns {boolean}
 */
export function isStoreAddressRequired(preciseOn) {
  return Boolean(preciseOn);
}

/**
 * @param {boolean} preciseOn
 * @param {unknown} rawValue
 * @returns {{ ok: true } | { ok: false, message: string, focusKey: string }}
 */
export function validateStoreAddress(preciseOn, rawValue) {
  if (!isStoreAddressRequired(preciseOn)) {
    return { ok: true };
  }
  const value = rawValue == null ? "" : String(rawValue).trim();
  if (!value) {
    return {
      ok: false,
      message: PRECISE_ADDRESS_REQUIRED_MSG,
      focusKey: "store_address",
    };
  }
  return { ok: true };
}

/**
 * @param {object} parameters
 * @returns {Record<string, unknown>}
 */
export function sanitizeEvaluateParameters(parameters) {
  const out = { ...parameters };
  out.use_precise_location = Boolean(out.use_precise_location);
  if (!out.use_precise_location) {
    delete out.store_address;
    // Temporary foot-traffic option requires a geocoded precise address.
    out.consider_temp_foot_traffic = false;
  } else {
    out.consider_temp_foot_traffic = Boolean(out.consider_temp_foot_traffic);
  }
  return out;
}

/**
 * After loading fails (HTTP or network), restore the last input step (inventory).
 * @param {number} stepsLength total STEPS including welcome
 * @returns {number}
 */
export function restoreStepIndexAfterEvaluateError(stepsLength) {
  const n = Number(stepsLength);
  if (!Number.isFinite(n) || n < 1) return 0;
  return n - 1;
}

/**
 * Panel visibility after evaluate error (loading ends, form returns).
 * @returns {{
 *   loadingHidden: boolean,
 *   inputHidden: boolean,
 *   stepProgressHidden: boolean,
 *   formErrorHidden: boolean,
 * }}
 */
export function evaluateErrorUiState() {
  return {
    loadingHidden: true,
    inputHidden: false,
    stepProgressHidden: false,
    formErrorHidden: false,
  };
}

/**
 * Normalize FastAPI / network error payloads into a short Korean message.
 * @param {unknown} detail
 * @param {string} fallback
 * @returns {string}
 */
export function formatApiError(detail, fallback) {
  if (detail == null || detail === "") return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const loc = Array.isArray(item.loc) ? item.loc.join(".") : "";
          const msg = item.msg || item.message || JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : String(msg);
        }
        return String(item);
      })
      .filter(Boolean)
      .join(" · ");
  }
  if (typeof detail === "object") {
    if (typeof detail.message === "string") return detail.message;
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }
  return String(detail);
}
