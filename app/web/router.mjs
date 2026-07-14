/** Hash-based view router for split main / result / dashboard / settings. */

export const ROUTES = {
  home: "home",
  run: "run",
  dashboard: "dashboard",
  settings: "settings",
};

const HASH_TO_ROUTE = {
  "": ROUTES.home,
  "/": ROUTES.home,
  "/home": ROUTES.home,
  "/upload": ROUTES.home,
  "/run": ROUTES.run,
  "/result": ROUTES.run,
  "/dashboard": ROUTES.dashboard,
  "/history": ROUTES.dashboard,
  "/settings": ROUTES.settings,
};

const ROUTE_TO_VIEW = {
  [ROUTES.home]: "view-upload",
  [ROUTES.run]: "view-result",
  [ROUTES.dashboard]: "view-dashboard",
  [ROUTES.settings]: "view-settings",
};

const ROUTE_TO_HASH = {
  [ROUTES.home]: "#/",
  [ROUTES.run]: "#/run",
  [ROUTES.dashboard]: "#/dashboard",
  [ROUTES.settings]: "#/settings",
};

export function parseRoute(hash = typeof location !== "undefined" ? location.hash : "") {
  const raw = (hash || "").replace(/^#/, "").trim();
  const path = raw === "" ? "/" : raw.startsWith("/") ? raw : `/${raw}`;
  // strip query fragment if any
  const bare = path.split("?")[0] || "/";
  return HASH_TO_ROUTE[bare] || ROUTES.home;
}

export function viewIdForRoute(route) {
  return ROUTE_TO_VIEW[route] || ROUTE_TO_VIEW[ROUTES.home];
}

export function hashForRoute(route) {
  return ROUTE_TO_HASH[route] || ROUTE_TO_HASH[ROUTES.home];
}

/**
 * @param {(id: string) => void} showView
 * @param {{
 *   onBeforeRoute?: (route: string, prev: string) => boolean | void,
 *   onAfterRoute?: (route: string) => void,
 *   hasResult?: () => boolean,
 * }} [options]
 */
export function createRouter(showView, options = {}) {
  let current = ROUTES.home;
  let syncing = false;

  function applyRoute(route, { writeHash = true } = {}) {
    const next = ROUTE_TO_VIEW[route] ? route : ROUTES.home;
    if (options.onBeforeRoute) {
      const ok = options.onBeforeRoute(next, current);
      if (ok === false) {
        // revert hash to current
        syncing = true;
        if (typeof location !== "undefined") {
          location.hash = hashForRoute(current).slice(1) === ""
            ? "#/"
            : hashForRoute(current);
        }
        syncing = false;
        return current;
      }
    }
    // result view requires a report in session
    if (next === ROUTES.run && options.hasResult && !options.hasResult()) {
      return applyRoute(ROUTES.home, { writeHash: true });
    }
    current = next;
    showView(viewIdForRoute(current));
    if (writeHash && typeof location !== "undefined") {
      const target = hashForRoute(current);
      if (location.hash !== target && location.hash !== target.replace("#/", "#")) {
        syncing = true;
        location.hash = target;
        syncing = false;
      }
    }
    document.querySelectorAll("[data-nav-route]").forEach((el) => {
      const active = el.getAttribute("data-nav-route") === current;
      el.classList.toggle("nav-link-active", active);
      if (el.tagName === "BUTTON" || el.getAttribute("role") === "link") {
        el.setAttribute("aria-current", active ? "page" : "false");
      }
    });
    options.onAfterRoute?.(current);
    return current;
  }

  function navigate(route) {
    return applyRoute(route, { writeHash: true });
  }

  function syncFromLocation() {
    if (syncing) return current;
    return applyRoute(parseRoute(location.hash), { writeHash: false });
  }

  function start() {
    window.addEventListener("hashchange", () => {
      if (syncing) return;
      syncFromLocation();
    });
    // initial
    if (!location.hash || location.hash === "#") {
      syncing = true;
      location.hash = "#/";
      syncing = false;
    }
    return syncFromLocation();
  }

  return {
    navigate,
    syncFromLocation,
    start,
    get current() {
      return current;
    },
    ROUTES,
  };
}
