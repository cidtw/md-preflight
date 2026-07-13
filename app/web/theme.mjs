/** Theme preference (light / dark / system). Move-only extract from app.js. */

const mql = typeof window !== "undefined" ? window.matchMedia("(prefers-color-scheme: dark)") : null;

export function applyTheme(pref) {
  if (typeof document === "undefined") return;
  const dark = pref === "dark" || (pref === "system" && mql?.matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  document.documentElement.dataset.themePref = pref;
  document.querySelectorAll(".theme-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.themeSet === pref),
  );
}

export function initTheme() {
  if (typeof document === "undefined" || !mql) return;
  let pref = "system";
  try {
    pref = localStorage.getItem("mdp-theme") || "system";
  } catch (_) {}
  applyTheme(pref);
  document.querySelectorAll(".theme-btn").forEach((b) =>
    b.addEventListener("click", () => {
      const p = b.dataset.themeSet;
      try {
        localStorage.setItem("mdp-theme", p);
      } catch (_) {}
      applyTheme(p);
    }),
  );
  // 시스템 모드일 때 OS 테마 변경을 실시간 반영
  mql.addEventListener("change", () => {
    if ((document.documentElement.dataset.themePref || "system") === "system") {
      applyTheme("system");
    }
  });
}
