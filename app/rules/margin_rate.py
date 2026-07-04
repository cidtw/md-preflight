from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class LowMarginRateRule:
    code: str = "LOW_MARGIN_RATE"
    severity: Severity = Severity.WARNING
    description: str = "Margin rate must stay above the configured minimum."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.joined
        eligible = (
            frame["promo_price"].notna()
            & frame["cost"].notna()
            & (frame["promo_price"] > 0)
        )
        margin_rate = pd.Series([0.0] * len(frame), index=frame.index, dtype="float64")
        margin_rate.loc[eligible] = (
            (frame.loc[eligible, "promo_price"] - frame.loc[eligible, "cost"])
            / frame.loc[eligible, "promo_price"]
        )
        invalid = eligible & (margin_rate < ctx.thresholds.min_margin_rate)
        for row in frame.loc[invalid].itertuples(index=False):
            promotion_id = str(row.promotion_id)
            product_code = str(row.product_code)
            source_row = int(str(row.source_row))
            promo_price = float(str(row.promo_price))
            cost = float(str(row.cost))
            current_margin_rate = (promo_price - cost) / promo_price
            issue_severity = Severity.ERROR if current_margin_rate < 0 else Severity.WARNING
            issues.append(
                make_issue(
                    code=self.code,
                    severity=issue_severity,
                    title="마진율이 기준보다 낮습니다",
                    message="행사가 기준 마진율이 최소 기준을 충족하지 못했습니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=source_row,
                    column="promo_price",
                    entity=RowEntity(
                        promotion_id=promotion_id,
                        product_code=product_code,
                    ),
                    observed=f"margin_rate={current_margin_rate:.2%}",
                    expected=f"margin_rate >= {ctx.thresholds.min_margin_rate:.2%}",
                    suggestion="행사가를 조정하거나 원가를 재검토하세요.",
                )
            )
        return issues


LOW_MARGIN_RATE_RULE = LowMarginRateRule()
