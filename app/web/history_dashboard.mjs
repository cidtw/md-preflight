function formatBucketDate(bucket) {
  return String(bucket).slice(0, 10);
}

function formatRuleSummary(run, displayLabel) {
  if (!Array.isArray(run.rules_triggered) || run.rules_triggered.length === 0) {
    return "문제 없음";
  }
  return run.rules_triggered
    .map((rule) => `${displayLabel(rule.code)} ${rule.count}건`)
    .join(" · ");
}

export function renderHistoryDashboard(host, historyState, displayLabel, loadHistory) {
  host.innerHTML = "";
  const controls = document.createElement("div");
  controls.className = "dashboard-controls";
  ["day", "month", "year"].forEach((granularity) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `btn ${historyState.granularity === granularity ? "btn-primary" : "btn-secondary"}`;
    button.textContent = granularity === "day" ? "일별" : granularity === "month" ? "월별" : "연별";
    button.addEventListener("click", () => {
      void loadHistory(granularity);
    });
    controls.append(button);
  });
  host.append(controls);

  if (historyState.buckets.length === 0) {
    const empty = document.createElement("p");
    empty.className = "caption mute";
    empty.textContent = "아직 저장된 검수 이력이 없습니다.";
    host.append(empty);
    return;
  }

  const chart = document.createElement("div");
  chart.className = "history-chart";
  const maxRuns = Math.max(...historyState.buckets.map((bucket) => bucket.run_count), 1);
  historyState.buckets.forEach((bucket) => {
    const card = document.createElement("div");
    card.className = "history-bar-card";
    card.style.setProperty("--bar-scale", String(bucket.run_count / maxRuns));
    card.append(buildTextNode("div", "history-bar-value", `${bucket.run_count}회`));
    card.append(buildTextNode("div", "history-bar", ""));
    card.append(buildTextNode("div", "history-bar-label", formatBucketDate(bucket.bucket)));
    chart.append(card);
  });
  host.append(chart);

  const table = document.createElement("table");
  table.className = "history-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>구간</th>
        <th>검수 수</th>
        <th>error 합계</th>
        <th>warning 합계</th>
        <th>통과율</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;
  const tbody = table.querySelector("tbody");
  historyState.buckets.forEach((bucket) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${formatBucketDate(bucket.bucket)}</td>
      <td>${bucket.run_count}</td>
      <td>${bucket.error_total}</td>
      <td>${bucket.warning_total}</td>
      <td>${Math.round(bucket.passed_rate * 100)}%</td>
    `;
    tbody.append(row);
  });
  host.append(table);

  const runsSection = document.createElement("section");
  runsSection.className = "history-run-log";
  runsSection.append(buildTextNode("h3", "history-run-log-title", "실행 로그"));
  const runsList = document.createElement("div");
  runsList.className = "history-run-list";
  historyState.runs.forEach((run) => {
    const item = document.createElement("article");
    item.className = "history-run-item";
    item.append(buildTextNode("div", "history-run-time", formatBucketDate(run.created_at)));
    item.append(buildTextNode("div", `history-run-badge ${run.passed ? "is-pass" : "is-fail"}`, run.passed ? "통과" : "실패"));
    item.append(buildTextNode("div", "history-run-meta", `error ${run.error_count} · warning ${run.warning_count} · total ${run.total_issues}`));
    item.append(buildTextNode("div", "history-run-rules", formatRuleSummary(run, displayLabel)));
    runsList.append(item);
  });
  runsSection.append(runsList);
  host.append(runsSection);
}

function buildTextNode(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}
