import { groupIssuesByFile, sevRank, buildReviewStatusBadge, createIssueView } from "../app/web/issue_view.mjs";

if (sevRank("warning") !== 2) throw new Error("sevRank");
const g = groupIssuesByFile([
  { location: { file: "a" } },
  { location: { file: "a" } },
  { location: { file: "b" } },
  {},
]);
if (g.a.length !== 2 || g.b.length !== 1) throw new Error("group");

function el(tag, cls, text) {
  const node = {
    tag,
    className: cls || "",
    textContent: text ?? "",
    children: [],
    style: {},
    get childNodes() {
      return this.children;
    },
    append(...nodes) {
      this.children.push(...nodes);
      return this;
    },
    addEventListener() {},
  };
  return node;
}

const badge = buildReviewStatusBadge(el, { status: "failed", severity: "error" });
if (!badge.className.includes("status-failed") || !badge.className.includes("sev-error")) {
  throw new Error("failed badge");
}

const state = { reviewResults: {} };
const view = createIssueView({
  el,
  state,
  SOURCE_LABELS: { promotion_plan: "프로모션 계획" },
  displayLabel: (k) => k,
  jumpToIssueLocation: () => {},
  FIELDS: [{ key: "promotion_plan" }],
});
const host = el("div");
view.renderIssueGroups(
  [
    {
      severity: "error",
      code: "INVALID_PROMO_PRICE",
      title: "가격 오류",
      location: { file: "promotion_plan", row: 3, column: "promo_price" },
      entity: { product_code: "P1" },
    },
  ],
  host,
);
if (host.children.length !== 1) throw new Error("expected one issue group");
console.log("issue_view verification passed");
