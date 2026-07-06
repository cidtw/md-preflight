from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class ExtremeDiscountRateRule:
    code: str = "EXTREME_DISCOUNT_RATE"
    severity: Severity = Severity.WARNING
    description: str = "Discount rate must stay below the configured maximum."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.joined
        eligible = (
            frame["normal_price"].notna()
            & frame["promo_price"].notna()
            & (frame["normal_price"] > 0)
            & (frame["promo_price"] > 0)
            & (frame["promo_price"] <= frame["normal_price"])
        )
        discount_rate = pd.Series([0.0] * len(frame), index=frame.index, dtype="float64")
        discount_rate.loc[eligible] = (
            1 - (frame.loc[eligible, "promo_price"] / frame.loc[eligible, "normal_price"])
        )
        invalid = eligible & (discount_rate >= ctx.thresholds.max_discount_rate)
        for row in frame.loc[invalid].itertuples(index=False):
            promotion_id = str(row.promotion_id)
            product_code = str(row.product_code)
            source_row = int(str(row.source_row))
            promo_price = float(str(row.promo_price))
            normal_price = float(str(row.normal_price))
            discount = 1 - (promo_price / normal_price)
            entity = RowEntity(
                promotion_id=promotion_id,
                product_code=product_code,
            )
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="할인율이 너무 큽니다",
                    message="설정된 최대 할인율을 초과했습니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=source_row,
                    column="promo_price",
                    entity=entity,
                    related=None,
                    observed=f"discount_rate={discount:.2%}",
                    expected=f"discount_rate < {ctx.thresholds.max_discount_rate:.2%}",
                    suggestion="할인율을 줄이거나 프로모션 구조를 다시 검토하세요.",
                )
            )
        return issues


EXTREME_DISCOUNT_RATE_RULE = ExtremeDiscountRateRule()
