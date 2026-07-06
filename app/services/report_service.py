from __future__ import annotations

from app.schemas.report import PreflightReport


def render_markdown_report(report: PreflightReport) -> str:
    lines = [
        "# MD Preflight Report",
        "",
        f"- Run ID: `{report.run_id}`",
        f"- Created At (UTC): {report.created_at.isoformat()}",
        f"- Total Issues: {report.summary.total_issues}",
        f"- Passed: {report.summary.passed}",
        f"- Checked Rows: {report.summary.checked_rows}",
        "",
        "## Summary",
        "",
        report.ai_summary or "요약 없음",
        "",
        "## Checklist",
        "",
    ]
    lines.extend(f"- {item}" for item in report.checklist)
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
