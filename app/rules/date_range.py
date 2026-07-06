from __future__ import annotations

from dataclasses import dataclass

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class InvalidDateRangeRule:
    code: str = "INVALID_DATE_RANGE"
    severity: Severity = Severity.ERROR
    description: str = "Start date must be parseable and on or before the end date."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.promotions
        invalid = frame["start_date"].isna() | frame["end_date"].isna() | (
            frame["start_date"] > frame["end_date"]
        )
        for row in frame.loc[invalid].itertuples(index=False):
            promotion_id = str(row.promotion_id)
            product_code = str(row.product_code)
            source_row = int(str(row.source_row))
            start_date_raw = str(row.start_date_raw)
            end_date_raw = str(row.end_date_raw)
            entity = RowEntity(
                promotion_id=promotion_id,
                product_code=product_code,
            )
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="행사 기간이 올바르지 않습니다",
                    message="시작일과 종료일을 확인해야 합니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=source_row,
                    column="start_date",
                    entity=entity,
                    related=None,
                    observed=f"start={start_date_raw}, end={end_date_raw}",
                    expected="start_date and end_date must be parseable and start_date <= end_date",
                    suggestion="행사 시작일과 종료일을 다시 입력하세요.",
                )
            )
        return issues


INVALID_DATE_RANGE_RULE = InvalidDateRangeRule()
