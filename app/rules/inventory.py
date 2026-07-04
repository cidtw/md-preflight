from __future__ import annotations

from dataclasses import dataclass

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class InventoryShortageRiskRule:
    code: str = "INVENTORY_SHORTAGE_RISK"
    severity: Severity = Severity.WARNING
    description: str = "Expected demand must not exceed the available stock quantity."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.joined
        invalid = (
            frame["expected_demand"].notna()
            & frame["stock_qty"].notna()
            & (frame["expected_demand"] > frame["stock_qty"])
        )
        for row in frame.loc[invalid].itertuples(index=False):
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="예상 수요 대비 재고가 부족합니다",
                    message="예상 수요가 현재 재고보다 많아 품절 위험이 있습니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=int(str(row.source_row)),
                    column="product_code",
                    entity=RowEntity(
                        promotion_id=str(row.promotion_id),
                        product_code=str(row.product_code),
                    ),
                    observed=(
                        f"expected_demand={float(str(row.expected_demand)):.1f}, "
                        f"stock_qty={float(str(row.stock_qty)):.1f}"
                    ),
                    expected="expected_demand <= stock_qty",
                    suggestion="예상 수요를 재검토하거나 재고를 추가 확보하세요.",
                )
            )
        return issues


INVENTORY_SHORTAGE_RISK_RULE = InventoryShortageRiskRule()
