import { buildServiceRequestUrl } from "../app/web/source_request.mjs";

const url = buildServiceRequestUrl("Airtable", "sync promotion rows");
const parsed = new URL(url);

if (!parsed.searchParams.get("title")?.includes("Airtable")) {
  throw new Error("source request title encoding failed");
}
if (!parsed.searchParams.get("body")?.includes("sync promotion rows")) {
  throw new Error("source request body encoding failed");
}

console.log("source request verification passed");
