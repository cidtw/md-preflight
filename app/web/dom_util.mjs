/** DOM helpers shared across UI modules. Move-only extract from app.js. */

export const $ = (sel) => document.querySelector(sel);

export function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

export function ext(name) {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i).toLowerCase();
}

export function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

let toastTimer;

/**
 * @param {string} msg
 * @param {{ durationMs?: number, multiline?: boolean }} [opts]
 */
export function toast(msg, opts = {}) {
  const t = $("#toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.toggle("toast-multiline", Boolean(opts.multiline || (msg && msg.includes("\n"))));
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  const duration = opts.durationMs ?? (opts.multiline || (msg && msg.includes("\n")) ? 8000 : 4000);
  toastTimer = setTimeout(() => t.classList.add("hidden"), duration);
}

export const VIEW_IDS = [
  "view-upload",
  "view-loading",
  "view-result",
  "view-dashboard",
  "view-settings",
];

export function showView(id) {
  VIEW_IDS.forEach((v) => $(`#${v}`)?.classList.toggle("hidden", v !== id));
}
