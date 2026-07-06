export function buildServiceRequestUrl(serviceName, details) {
  const title = `[Source Request] ${serviceName}`;
  const body = [
    "## Requested Service",
    serviceName,
    "",
    "## Desired Features",
    details || "(please describe the workflow you want)",
  ].join("\n");
  const params = new URLSearchParams({
    title,
    body,
  });
  return `https://github.com/cidtw/md-preflight/issues/new?${params.toString()}`;
}
