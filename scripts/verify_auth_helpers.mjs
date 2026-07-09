globalThis.window = {};

const {
  getAuthMode,
  getClerkPublishableKey,
  hasClerkMode,
  isAuthUnavailable,
  isStubAuthAvailable,
} = await import("../app/web/auth_helpers.mjs");

// No config injected at all -> secure default, not "assume stub works".
window.__MDP_CONFIG__ = undefined;
if (getAuthMode() !== "off") {
  throw new Error("missing config should default to auth_mode=off");
}
if (isStubAuthAvailable() || !isAuthUnavailable()) {
  throw new Error("missing config should report auth unavailable, not stub-available");
}

window.__MDP_CONFIG__ = { authMode: "stub" };
if (getAuthMode() !== "stub" || !isStubAuthAvailable() || isAuthUnavailable()) {
  throw new Error("stub auth_mode not read correctly");
}

window.__MDP_CONFIG__ = { authMode: "clerk", clerkPublishableKey: "pk_test_x" };
if (getAuthMode() !== "clerk" || isStubAuthAvailable() || isAuthUnavailable()) {
  throw new Error("clerk auth_mode not read correctly");
}
if (getClerkPublishableKey() !== "pk_test_x" || !hasClerkMode()) {
  throw new Error("clerk publishable key not read correctly");
}

window.__MDP_CONFIG__ = { authMode: "off" };
if (!isAuthUnavailable() || isStubAuthAvailable()) {
  throw new Error("off auth_mode not read correctly");
}

// Unknown/corrupt value falls back to the secure default, never to stub.
window.__MDP_CONFIG__ = { authMode: "something-unexpected" };
if (getAuthMode() !== "off") {
  throw new Error("unknown auth_mode should fall back to off, not stub");
}

console.log("auth helpers verification passed");
