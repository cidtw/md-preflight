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
