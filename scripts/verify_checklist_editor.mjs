import { sanitizeChecklistCellValue } from "../app/web/editor_state.mjs";

if (sanitizeChecklistCellValue("start_date=2026-07-15", "start_date") !== "2026-07-15") {
  throw new Error("column prefix should be removed before writing to CSV");
}

if (sanitizeChecklistCellValue("  promo_price = 9900", "promo_price") !== "9900") {
  throw new Error("whitespace around prefix should still be handled");
}

if (sanitizeChecklistCellValue("2026-07-15", "start_date") !== "2026-07-15") {
  throw new Error("bare values should pass through untouched");
}

console.log("checklist editor verification passed");
