from __future__ import annotations

from dataclasses import dataclass

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue, normalize_related_row
from app.schemas.issue import IssueLocation, Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class InboundDateConflictRule:
    code: str = "INBOUND_DATE_CONFLICT"
    severity: Severity = Severity.WARNING
    description: str = "Inbound inventory should arrive on or before the promotion start date."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.joined
        invalid = (
            frame["inbound_date"].notna()
            & frame["start_date"].notna()
            & (frame["inbound_date"] > frame["start_date"])
        )
        for row in frame.loc[invalid].itertuples(index=False):
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="입고일이 행사 시작일보다 늦습니다",
                    message="행사 시작 전에 재고가 입고되지 않아 운영 차질이 예상됩니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=int(str(row.source_row)),
                    column="start_date",
                    entity=RowEntity(
                        promotion_id=str(row.promotion_id),
                        product_code=str(row.product_code),
                    ),
                    related=[
                        IssueLocation(
                            file=SourceFile.INVENTORY.value,
                            row=normalize_related_row(getattr(row, "inventory_source_row", None)),
                            column="inbound_date",
                        )
                    ],
                    observed=(
                        "inbound_date="
                        f"{str(row.inbound_date)[:10]}, start_date={str(row.start_date)[:10]}"
                    ),
                    expected="inbound_date <= start_date",
                    suggestion="입고 일정을 앞당기거나 행사 시작일을 조정하세요.",
                )
            )
        return issues


INBOUND_DATE_CONFLICT_RULE = InboundDateConflictRule()
