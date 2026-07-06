import { buildAuthHeaders, isSignedIn } from "../app/web/auth_helpers.mjs";
import { buildHistoryUrl, normalizeGranularity } from "../app/web/history_helpers.mjs";

const signedIn = { signedIn: true, userId: "demo-user" };
const signedOut = { signedIn: false, userId: null };

if (!isSignedIn(signedIn) || isSignedIn(signedOut)) {
  throw new Error("auth gate helper broke");
}

if (buildAuthHeaders(signedIn)["x-md-preflight-user-id"] !== "demo-user") {
  throw new Error("signed-in auth header is missing");
}

if (Object.keys(buildAuthHeaders(signedOut)).length !== 0) {
  throw new Error("signed-out auth header should be empty");
}

if (normalizeGranularity("week") !== "day") {
  throw new Error("invalid granularity should fall back to day");
}

if (buildHistoryUrl("month") !== "/api/preflight/history?granularity=month") {
  throw new Error("history URL builder broke");
}

console.log("history dashboard verification passed");
