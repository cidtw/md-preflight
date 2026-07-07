const ALLOWED_GRANULARITIES = new Set(["day", "month", "year"]);

export function normalizeGranularity(granularity) {
  return ALLOWED_GRANULARITIES.has(granularity) ? granularity : "day";
}

export function buildHistoryUrl(granularity) {
  const safeGranularity = normalizeGranularity(granularity);
  return `/api/preflight/history?granularity=${encodeURIComponent(safeGranularity)}`;
}

export function buildHistoryRunsUrl(limit = 50) {
  const safeLimit = Number.isInteger(limit) && limit > 0 ? Math.min(limit, 100) : 50;
  return `/api/preflight/history/runs?limit=${encodeURIComponent(String(safeLimit))}`;
}
