export function isSignedIn(auth) {
  return Boolean(auth?.signedIn && auth?.userId);
}

export function buildAuthHeaders(auth) {
  if (!isSignedIn(auth)) {
    return {};
  }
  return { "x-md-preflight-user-id": auth.userId };
}
