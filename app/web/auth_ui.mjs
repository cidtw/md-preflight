/**
 * Auth session UI (Clerk + stub). Move-only extract from app.js.
 * Inject app-owned state and cross-module callbacks via createAuthUi(deps).
 */
import {
  buildAuthHeaders,
  getClerkPublishableKey,
  hasClerkMode,
  isAuthUnavailable,
  isSignedIn,
  isStubAuthAvailable,
} from "./auth_helpers.mjs";

/**
 * @param {object} deps
 * @param {object} deps.state - app state (mutates state.auth / state.history)
 * @param {(sel: string) => Element|null} deps.$
 * @param {(msg: string) => void} deps.toast
 * @param {(id: string) => void} deps.showView
 * @param {() => void} deps.renderDashboard
 * @param {(granularity?: string) => Promise<void>} deps.loadHistory
 */
export function createAuthUi(deps) {
  const { state, $, toast, showView, renderDashboard, loadHistory } = deps;

  async function authHeaders() {
    await refreshAuthSession();
    return buildAuthHeaders(state.auth);
  }

  function persistAuth() {
    if (state.auth.provider !== "stub") {
      return;
    }
    try {
      localStorage.setItem("mdp-auth", JSON.stringify(state.auth));
    } catch (_) {}
  }

  function clerkDisplayName(user) {
    if (!user) return null;
    const fullName = typeof user.fullName === "string" ? user.fullName.trim() : "";
    if (fullName) return fullName;
    const username = typeof user.username === "string" ? user.username.trim() : "";
    if (username) return username;
    const first = typeof user.firstName === "string" ? user.firstName.trim() : "";
    const last = typeof user.lastName === "string" ? user.lastName.trim() : "";
    const combined = `${first} ${last}`.trim();
    if (combined) return combined;
    const email =
      user.primaryEmailAddress?.emailAddress ||
      user.emailAddresses?.[0]?.emailAddress ||
      "";
    if (typeof email === "string" && email.includes("@")) {
      return email.split("@")[0];
    }
    if (typeof email === "string" && email.trim()) return email.trim();
    return null;
  }

  function authStatusLabel() {
    if (!isSignedIn(state.auth)) {
      return isAuthUnavailable() ? "로그인 불가 — 이력은 Clerk 인증 필요" : "비로그인";
    }
    const name =
      (typeof state.auth.displayName === "string" && state.auth.displayName.trim()) ||
      null;
    // Never show raw Clerk ids like user_xxx in the nav chrome.
    if (name && !name.startsWith("user_")) {
      return name;
    }
    if (state.auth.provider === "stub") {
      return "데모 사용자";
    }
    return "로그인됨";
  }

  function renderAuthControls() {
    const signedIn = isSignedIn(state.auth);
    const authUnavailable = isAuthUnavailable();
    const status = $("#auth-status");
    if (status) {
      status.textContent = authStatusLabel();
      status.title = signedIn && state.auth.userId ? `계정 ID: ${state.auth.userId}` : "";
    }
    const login = $("#auth-login");
    const logout = $("#auth-logout");
    const dashboard = $("#nav-dashboard");
    if (login) {
      login.classList.toggle("hidden", signedIn);
      login.disabled = authUnavailable;
      login.title = authUnavailable
        ? "이 배포는 로그인이 설정되지 않았습니다. 검수 자체는 계속 이용 가능합니다."
        : "";
    }
    if (logout) {
      logout.classList.toggle("hidden", !signedIn);
    }
    if (dashboard) {
      dashboard.classList.toggle("hidden", !signedIn);
    }
  }

  function setSignedOutAuth() {
    state.auth = {
      signedIn: false,
      userId: null,
      displayName: null,
      sessionToken: null,
      provider: hasClerkMode() ? "clerk" : (isStubAuthAvailable() ? "stub" : "off"),
    };
  }

  function signInStub() {
    state.auth = {
      signedIn: true,
      userId: "demo-user",
      displayName: "데모 사용자",
      sessionToken: null,
      provider: "stub",
    };
    persistAuth();
    renderAuthControls();
    renderDashboard();
  }

  function signOutStub() {
    setSignedOutAuth();
    state.history = { granularity: "day", buckets: [], runs: [] };
    persistAuth();
    renderAuthControls();
    renderDashboard();
    if ($("#view-dashboard") && !$("#view-dashboard").classList.contains("hidden")) {
      showView("view-upload");
    }
  }

  function initAuth() {
    if (hasClerkMode() || !isStubAuthAvailable()) {
      // Stub sessions from a prior deploy can never authenticate against a
      // server that no longer accepts them — don't restore a fake "signed in".
      setSignedOutAuth();
      renderAuthControls();
      return;
    }
    try {
      const saved = JSON.parse(localStorage.getItem("mdp-auth") || "null");
      if (saved && typeof saved.signedIn === "boolean") {
        state.auth = {
          signedIn: Boolean(saved.signedIn),
          userId: typeof saved.userId === "string" ? saved.userId : null,
          displayName:
            typeof saved.displayName === "string" && saved.displayName.trim()
              ? saved.displayName.trim()
              : saved.userId === "demo-user"
                ? "데모 사용자"
                : null,
          sessionToken: null,
          provider: "stub",
        };
      }
    } catch (_) {}
    renderAuthControls();
  }

  function loadScript(src, attributes = {}) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        if (existing.dataset.loaded === "true") {
          resolve();
          return;
        }
        existing.addEventListener("load", () => resolve(), { once: true });
        existing.addEventListener(
          "error",
          () => reject(new Error(`스크립트를 불러오지 못했습니다: ${src}`)),
          { once: true },
        );
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.defer = true;
      script.crossOrigin = "anonymous";
      Object.entries(attributes).forEach(([name, value]) => {
        script.setAttribute(name, value);
      });
      script.addEventListener(
        "load",
        () => {
          script.dataset.loaded = "true";
          resolve();
        },
        { once: true },
      );
      script.addEventListener(
        "error",
        () => reject(new Error(`스크립트를 불러오지 못했습니다: ${src}`)),
        { once: true },
      );
      document.head.append(script);
    });
  }

  async function loadClerk() {
    const publishableKey = getClerkPublishableKey();
    if (!publishableKey) {
      return null;
    }
    const encodedDomain = publishableKey.split("_")[2];
    const clerkDomain = atob(encodedDomain).slice(0, -1);
    await Promise.all([
      loadScript(`https://${clerkDomain}/npm/@clerk/ui@1/dist/ui.browser.js`),
      loadScript(`https://${clerkDomain}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`, {
        "data-clerk-publishable-key": publishableKey,
      }),
    ]);
    await window.Clerk.load({
      ui: { ClerkUI: window.__internal_ClerkUICtor },
    });
    window.Clerk.addListener(() => {
      void syncAuthFromClerk();
    });
    await syncAuthFromClerk();
    return window.Clerk;
  }

  async function refreshAuthSession() {
    if (!hasClerkMode() || !window.Clerk?.loaded) {
      return;
    }
    const session = window.Clerk.session;
    const user = window.Clerk.user;
    if (!session || !user) {
      if (state.auth.signedIn) {
        signOutStub();
      }
      return;
    }
    const sessionToken = await session.getToken();
    state.auth = {
      signedIn: true,
      userId: user.id,
      displayName: clerkDisplayName(user),
      sessionToken,
      provider: "clerk",
    };
    renderAuthControls();
  }

  async function syncAuthFromClerk() {
    await refreshAuthSession();
    renderDashboard();
    if (isSignedIn(state.auth) && !$("#view-dashboard")?.classList.contains("hidden")) {
      await loadHistory(state.history.granularity);
    }
  }

  async function signIn() {
    if (!hasClerkMode()) {
      if (isAuthUnavailable()) {
        toast("로그인을 사용할 수 없습니다 — 이력 대시보드는 Clerk 인증이 필요합니다.");
        return;
      }
      signInStub();
      return;
    }
    if (!window.Clerk?.loaded) {
      toast("로그인 모듈을 아직 불러오지 못했습니다.");
      return;
    }
    await window.Clerk.openSignIn({
      withSignUp: true,
      fallbackRedirectUrl: window.location.href,
      signUpFallbackRedirectUrl: window.location.href,
    });
  }

  async function signOut() {
    if (!hasClerkMode()) {
      signOutStub();
      return;
    }
    if (!window.Clerk?.loaded) {
      signOutStub();
      return;
    }
    await window.Clerk.signOut();
    signOutStub();
  }

  return {
    authHeaders,
    persistAuth,
    clerkDisplayName,
    authStatusLabel,
    renderAuthControls,
    setSignedOutAuth,
    signInStub,
    signOutStub,
    initAuth,
    loadClerk,
    loadScript,
    refreshAuthSession,
    syncAuthFromClerk,
    signIn,
    signOut,
  };
}
