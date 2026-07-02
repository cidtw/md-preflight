from __future__ import annotations

from dataclasses import dataclass

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class InvalidPromoPriceRule:
    code: str = "INVALID_PROMO_PRICE"
    severity: Severity = Severity.ERROR
    description: str = "Promo price must be positive and not exceed the normal price."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.joined
        valid_master = frame["normal_price"].notna()
        invalid = valid_master & (
            frame["promo_price"].isna()
            | (frame["promo_price"] <= 0)
            | (frame["promo_price"] > frame["normal_price"])
        )
        for row in frame.loc[invalid].itertuples(index=False):
            promotion_id = str(row.promotion_id)
            product_code = str(row.product_code)
            source_row = int(str(row.source_row))
            promo_price_raw = str(row.promo_price_raw)
            normal_price = float(str(row.normal_price))
            entity = RowEntity(
                promotion_id=promotion_id,
                product_code=product_code,
            )
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="행사가가 정상가보다 높거나 유효하지 않습니다",
                    message="프로모션 가격은 0보다 커야 하고 정상가를 초과하면 안 됩니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=source_row,
                    column="promo_price",
                    entity=entity,
                    observed=f"promo_price={promo_price_raw}",
                    expected=f"0 < promo_price <= normal_price ({normal_price})",
                    suggestion="행사가를 정상가 이하의 양수로 다시 입력하세요.",
                )
            )
        return issues


INVALID_PROMO_PRICE_RULE = InvalidPromoPriceRule()
