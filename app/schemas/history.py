from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.issue import Severity
from app.schemas.report import PreflightReport


class RuleTrigger(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    code: str
    severity: Severity
    count: int


class RunHistoryRecord(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: int | None = None
    user_id: str
    run_id: str
    created_at: datetime
    passed: bool
    error_count: int
    warning_count: int
    total_issues: int
    rules_triggered: list[RuleTrigger] = Field(default_factory=list)
    source_label: str | None = None
    rule_set_version: str | None = None

    @classmethod
    def from_report(
        cls,
        user_id: str,
        run_id: str,
        report: PreflightReport,
        *,
        source_label: str | None = None,
    ) -> RunHistoryRecord:
        by_rule = Counter(issue.code for issue in report.issues)
        severities: dict[str, Severity] = {}
        for issue in report.issues:
            current = severities.get(issue.code)
            if current is None or severity_rank(issue.severity) > severity_rank(current):
                severities[issue.code] = issue.severity
        return cls(
            user_id=user_id,
            run_id=run_id,
            created_at=report.created_at,
            passed=report.summary.passed,
            error_count=report.summary.by_severity.get("error", 0),
            warning_count=report.summary.by_severity.get("warning", 0),
            total_issues=report.summary.total_issues,
            rules_triggered=[
                RuleTrigger(
                    code=code,
                    severity=severities[code],
                    count=count,
                )
                for code, count in sorted(by_rule.items())
            ],
            source_label=source_label,
            rule_set_version=report.rule_set_version,
        )


class HistoryBucket(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    bucket: datetime
    run_count: int
    error_total: int
    warning_total: int
    passed_rate: float


def severity_rank(severity: Severity) -> int:
    return {
        Severity.ERROR: 3,
        Severity.WARNING: 2,
        Severity.INFO: 1,
    }[severity]
