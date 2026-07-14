import { hashForRoute, parseRoute, ROUTES, viewIdForRoute } from "../app/web/router.mjs";

const cases = [
  ["", ROUTES.home],
  ["#/", ROUTES.home],
  ["#/upload", ROUTES.home],
  ["#/run", ROUTES.run],
  ["#/result", ROUTES.run],
  ["#/dashboard", ROUTES.dashboard],
  ["#/settings", ROUTES.settings],
  ["#/unknown", ROUTES.home],
];

for (const [hash, expected] of cases) {
  const got = parseRoute(hash);
  if (got !== expected) {
    throw new Error(`parseRoute(${hash}) => ${got}, expected ${expected}`);
  }
}

if (viewIdForRoute(ROUTES.settings) !== "view-settings") {
  throw new Error("viewId settings");
}
if (hashForRoute(ROUTES.dashboard) !== "#/dashboard") {
  throw new Error("hash dashboard");
}

console.log("router verification passed");
