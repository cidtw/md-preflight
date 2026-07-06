const ALLOWED_GRANULARITIES = new Set(["day", "month", "year"]);

export function normalizeGranularity(granularity) {
  return ALLOWED_GRANULARITIES.has(granularity) ? granularity : "day";
}

export function buildHistoryUrl(granularity) {
  const safeGranularity = normalizeGranularity(granularity);
  return `/api/preflight/history?granularity=${encodeURIComponent(safeGranularity)}`;
}
