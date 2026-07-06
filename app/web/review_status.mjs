export function issueKey(issue) {
  return [issue.code, issue.location?.file ?? "-", issue.location?.row ?? "-", issue.location?.column ?? "-"].join(":");
}

export function checklistItemKey(item) {
  return [item.code, item.file, item.row ?? "-", item.column ?? "-"].join(":");
}

export function diffIssueKeys(pendingKeys, newIssues, reviewItemsByKey = {}) {
  const newKeys = new Set(newIssues.map((issue) => issueKey(issue)));
  const failed = {};
  const fixed = {};

  pendingKeys.forEach((key) => {
    if (newKeys.has(key)) {
      const issue = newIssues.find((candidate) => issueKey(candidate) === key);
      failed[key] = { status: "failed", severity: issue?.severity ?? "warning" };
      return;
    }
    fixed[key] = {
      status: "fixed",
      severity: "info",
      item: reviewItemsByKey[key] ?? null,
    };
  });

  return { failed, fixed };
}
