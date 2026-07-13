/**
 * Issue list rendering. Move-only extract from app.js.
 */
import { issueKey } from "./review_status.mjs";

export const SEV_LABEL = { error: "error", warning: "warning", info: "info" };

export function sevRank(sev) {
  return { error: 3, warning: 2, info: 1 }[sev] || 0;
}

export function groupIssuesByFile(issues) {
  return issues.reduce((acc, issue) => {
    const file = issue.location?.file;
    if (!file) {
      return acc;
    }
    const bucket = acc[file] || [];
    bucket.push(issue);
    acc[file] = bucket;
    return acc;
  }, {});
}

export function buildReviewStatusBadge(el, review) {
  if (review.status === "fixed") {
    return el("span", "review-status status-fixed", "수정완료");
  }
  return el(
    "span",
    `review-status status-failed sev-${review.severity}`,
    "수정실패",
  );
}

function textNode(text) {
  if (typeof document !== "undefined" && document.createTextNode) {
    return document.createTextNode(text);
  }
  // Node verify / non-DOM hosts
  return { nodeType: 3, textContent: String(text) };
}

/**
 * @param {object} deps
 * @param {typeof import('./dom_util.mjs').el} deps.el
 * @param {object} deps.state
 * @param {Record<string,string>} deps.SOURCE_LABELS
 * @param {(key: string) => string} deps.displayLabel
 * @param {(location: object, related?: object[]) => void} deps.jumpToIssueLocation
 * @param {Array<{key: string}>} deps.FIELDS
 */
export function createIssueView(deps) {
  const { el, state, SOURCE_LABELS, displayLabel, jumpToIssueLocation, FIELDS } = deps;

  function renderIssue(iss) {
    const row = el("div", `issue-row sev-${iss.severity}`);

    row.append(el("span", `badge sev-${iss.severity}`, SEV_LABEL[iss.severity] || iss.severity));

    const bodyEl = el("div", "issue-body");
    bodyEl.append(el("div", "issue-title", iss.title || iss.code));
    if (iss.message) bodyEl.append(el("div", "issue-msg", iss.message));

    const detail = el("div", "issue-detail");
    const entity = iss.entity || {};
    Object.entries(entity).forEach(([k, v]) => {
      const span = el("span");
      span.append(textNode(`${displayLabel(k)}: `));
      span.append(el("b", null, String(v)));
      detail.append(span);
    });
    if (iss.observed != null) {
      const span = el("span");
      span.append(textNode("관측: "));
      span.append(el("b", null, String(iss.observed)));
      detail.append(span);
    }
    if (iss.expected != null) {
      const span = el("span");
      span.append(textNode("기대: "));
      span.append(el("b", null, String(iss.expected)));
      detail.append(span);
    }
    if (detail.childNodes.length) bodyEl.append(detail);
    if (iss.suggestion) {
      const sug = el("div", "issue-msg");
      sug.style.color = "var(--mute)";
      sug.textContent = `→ ${iss.suggestion}`;
      bodyEl.append(sug);
    }
    const review = state.reviewResults[issueKey(iss)];
    if (review) {
      bodyEl.append(buildReviewStatusBadge(el, review));
    }
    bodyEl.append(el("span", "rule-chip rule-chip-muted", iss.code));
    if (iss.location?.file) {
      const jump = el("button", "btn btn-ghost issue-jump-btn", "파일에서 보기");
      jump.type = "button";
      jump.addEventListener("click", () =>
        jumpToIssueLocation(iss.location, iss.related_locations || []),
      );
      bodyEl.append(jump);
    }
    row.append(bodyEl);

    const loc = iss.location || {};
    const locText = [
      SOURCE_LABELS[loc.file] ?? loc.file,
      loc.row != null ? `행 ${loc.row}` : null,
      loc.column ? displayLabel(loc.column) : null,
    ]
      .filter(Boolean)
      .join(" · ");
    row.append(el("span", "issue-loc", locText));

    return row;
  }

  function buildIssueGroup(label, issues) {
    const wrap = el("section", "issue-group");
    const head = el("div", "issue-group-head");
    const title = el("h3", "issue-group-title", label);
    const meta = el("div", "issue-group-meta");
    const errorCount = issues.filter((issue) => issue.severity === "error").length;
    const warningCount = issues.filter((issue) => issue.severity === "warning").length;
    const infoCount = issues.filter((issue) => issue.severity === "info").length;

    if (errorCount > 0) {
      meta.append(el("span", "issue-group-badge error", `error ${errorCount}`));
    }
    if (warningCount > 0) {
      meta.append(el("span", "issue-group-badge warning", `warning ${warningCount}`));
    }
    if (infoCount > 0) {
      meta.append(el("span", "issue-group-badge info", `info ${infoCount}`));
    }

    head.append(title);
    head.append(meta);
    wrap.append(head);

    const list = el("div", "issue-list");
    const sorted = [...issues].sort(
      (a, b) => sevRank(b.severity) - sevRank(a.severity) || a.code.localeCompare(b.code),
    );
    sorted.forEach((issue) => list.append(renderIssue(issue)));
    wrap.append(list);
    return wrap;
  }

  function renderIssueGroups(issues, host) {
    const grouped = groupIssuesByFile(issues);
    const commonIssues = issues.filter((issue) => !issue.location?.file);

    FIELDS.forEach((field) => {
      const fileIssues = grouped[field.key] || [];
      if (fileIssues.length === 0) {
        return;
      }
      host.append(buildIssueGroup(SOURCE_LABELS[field.key], fileIssues));
    });

    if (commonIssues.length > 0) {
      host.append(buildIssueGroup("공통 / 교차 참조", commonIssues));
    }
  }

  return {
    SEV_LABEL,
    sevRank,
    groupIssuesByFile,
    buildReviewStatusBadge: (review) => buildReviewStatusBadge(el, review),
    renderIssue,
    buildIssueGroup,
    renderIssueGroups,
  };
}
