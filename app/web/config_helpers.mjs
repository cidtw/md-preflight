const DEFAULT_MAX_BYTES = 5 * 1024 * 1024;
const DEFAULT_ALLOWED_EXTENSIONS = [".csv", ".xlsx"];

// Server injects real limits via window.__MDP_CONFIG__ (see build_index_html).
// Defaults here only cover contexts where that injection didn't happen
// (e.g. app.js loaded outside the FastAPI-rendered index page).
export function getUploadLimits() {
  const config = window.__MDP_CONFIG__ || {};
  const maxBytes =
    Number.isFinite(config.maxUploadBytes) && config.maxUploadBytes > 0
      ? config.maxUploadBytes
      : DEFAULT_MAX_BYTES;
  const allowedExtensions =
    Array.isArray(config.allowedExtensions) && config.allowedExtensions.length > 0
      ? config.allowedExtensions
      : DEFAULT_ALLOWED_EXTENSIONS;
  return { maxBytes, allowedExtensions };
}
