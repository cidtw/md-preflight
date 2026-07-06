import { diffIssueKeys, issueKey } from "../app/web/review_status.mjs";

const issue = {
  code: "LOW_MARGIN_RATE",
  location: { file: "promotion_plan", row: 6, column: "promo_price" },
  severity: "warning",
};
const fixedKey = "EXTREME_DISCOUNT_RATE:promotion_plan:4:promo_price";
const pending = new Set([issueKey(issue), fixedKey]);
const diff = diffIssueKeys(pending, [issue], {
  [fixedKey]: { code: "EXTREME_DISCOUNT_RATE", file: "promotion_plan", row: 4, column: "promo_price" },
});

if (diff.failed[issueKey(issue)]?.status !== "failed") {
  throw new Error("failed issue detection broke");
}
if (diff.fixed[fixedKey]?.status !== "fixed") {
  throw new Error("fixed issue detection broke");
}

console.log("review status verification passed");
