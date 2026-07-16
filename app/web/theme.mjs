/**
 * Theme control (v1 MD Preflight style).
 * Preference: light | dark | system
 * Resolved theme applied as data-theme="light"|"dark" on <html>.
 */

const THEME_KEY = "rop-theme-mode";

/** @returns {"light"|"dark"|"system"} */
export function readThemePreference() {
  const raw = localStorage.getItem(THEME_KEY);
  if (raw === "light" || raw === "dark" || raw === "system") return raw;
  return "system";
}

/** @returns {"light"|"dark"} */
export function resolveTheme(pref) {
  const p = pref === "light" || pref === "dark" || pref === "system" ? pref : "system";
  if (p === "light" || p === "dark") return p;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyThemePreference(pref) {
  const preference =
    pref === "light" || pref === "dark" || pref === "system" ? pref : "system";
  localStorage.setItem(THEME_KEY, preference);
  const resolved = resolveTheme(preference);
  document.documentElement.dataset.theme = resolved;
  document.documentElement.dataset.themePref = preference;
  document.querySelectorAll("[data-theme-btn]").forEach((btn) => {
    const mode = btn.getAttribute("data-theme-btn");
    btn.classList.toggle("active", mode === preference);
    btn.setAttribute("aria-pressed", mode === preference ? "true" : "false");
  });
  return resolved;
}

export function initTheme() {
  applyThemePreference(readThemePreference());
  document.querySelectorAll("[data-theme-btn]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.getAttribute("data-theme-btn");
      if (mode) applyThemePreference(mode);
    });
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (readThemePreference() === "system") applyThemePreference("system");
  });
}
