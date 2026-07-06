from dataclasses import dataclass
from typing import Protocol

from app.domain.context import PreflightContext
from app.schemas.issue import IssueLocation, Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


class Rule(Protocol):
    @property
    def code(self) -> str: ...

    @property
    def severity(self) -> Severity: ...

    @property
    def description(self) -> str: ...

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]: ...

    def meta(self) -> RuleMeta: ...


@dataclass(frozen=True, slots=True)
class RowEntity:
    promotion_id: str
    product_code: str


def normalize_related_row(value: object) -> int | None:
    text = str(value).strip().lower()
    if text in {"", "nan", "none"}:
        return None
    return int(float(text))


def make_issue(
    *,
    code: str,
    severity: Severity,
    title: str,
    message: str,
    file: str,
    row: int | None,
    column: str | None,
    entity: RowEntity,
    related: list[IssueLocation] | None,
    observed: str | None,
    expected: str | None,
    suggestion: str | None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity=severity,
        title=title,
        message=message,
        entity={
            "promotion_id": entity.promotion_id,
            "product_code": entity.product_code,
        },
        location=IssueLocation(file=file, row=row, column=column),
        related_locations=[] if related is None else related,
        observed=observed,
        expected=expected,
        suggestion=suggestion,
    )
