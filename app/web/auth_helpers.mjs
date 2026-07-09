export function isSignedIn(auth) {
  return Boolean(auth?.signedIn && auth?.userId);
}

export function buildAuthHeaders(auth) {
  if (!isSignedIn(auth)) {
    return {};
  }
  if (typeof auth.sessionToken === "string" && auth.sessionToken.length > 0) {
    return { Authorization: `Bearer ${auth.sessionToken}` };
  }
  return { "x-md-preflight-user-id": auth.userId };
}

export function getClerkPublishableKey() {
  return window.__MDP_CONFIG__?.clerkPublishableKey || null;
}

export function hasClerkMode() {
  return typeof getClerkPublishableKey() === "string" && getClerkPublishableKey().length > 0;
}

// Server-derived auth_mode ("clerk" | "stub" | "off") — see Settings.auth_mode.
// Falls back to "off" (the secure default) if the config wasn't injected for
// some reason, rather than silently assuming stub auth is available.
export function getAuthMode() {
  const mode = window.__MDP_CONFIG__?.authMode;
  return mode === "clerk" || mode === "stub" ? mode : "off";
}

export function isStubAuthAvailable() {
  return getAuthMode() === "stub";
}

export function isAuthUnavailable() {
  return getAuthMode() === "off";
}
