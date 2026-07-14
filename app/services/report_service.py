from __future__ import annotations

from app.schemas.report import PreflightReport


def render_markdown_report(report: PreflightReport) -> str:
    lines = [
        "# MD Preflight Report",
        "",
        f"- Run ID: `{report.run_id}`",
        f"- Rule Set Version: `{report.rule_set_version}`",
        f"- Created At (UTC): {report.created_at.isoformat()}",
        f"- Total Issues: {report.summary.total_issues}",
        f"- Passed: {report.summary.passed}",
        f"- Checked Rows: {report.summary.checked_rows}",
        "",
        "## Summary",
        "",
        report.ai_summary or "요약 없음",
        "",
        "## Per-file Summary",
        "",
    ]
    lines.extend(
        f"- {item.file}: {item.issue_count}건 · {item.headline}" for item in report.file_summaries
    )
    if report.column_mappings:
        lines.extend(
            [
                "",
                "## Column Mapping",
                "",
                "Uploaded headers renamed to canonical rule keys:",
                "",
            ]
        )
        lines.extend(
            f"- `{item.file}`: `{item.original}` → `{item.canonical}`"
            for item in report.column_mappings
        )
    else:
        lines.extend(
            [
                "",
                "## Column Mapping",
                "",
                "No header aliases applied (columns already canonical).",
                "",
            ]
        )
    lines.extend(
        [
            "",
        "## Checklist",
        "",
        ]
    )
    lines.extend(f"- {item}" for item in report.checklist)
    if report.checklist_items:
        lines.extend(
            [
                "",
                "## Checklist Items",
                "",
            ]
        )
        lines.extend(
            (
                f"- [{item.code}] {item.file}:{item.row}:{item.column} | "
                f"current={item.current or '-'} | suggested={item.suggested or '-'} | "
                f"{item.rationale}"
            )
            for item in report.checklist_items
        )
    lines.extend(
        [
            "",
            "## Issues",
            "",
        ]
    )
    for issue in report.issues:
        lines.extend(
            [
                f"### {issue.code}",
                f"- Severity: {issue.severity.value}",
                f"- Location: {issue.location.file}:{issue.location.row}",
                f"- Entity: {issue.entity['promotion_id']} / {issue.entity['product_code']}",
                f"- Observed: {issue.observed or '-'}",
                f"- Expected: {issue.expected or '-'}",
                f"- Suggestion: {issue.suggestion or '-'}",
                "",
            ]
        )
    return "\n".join(lines)
