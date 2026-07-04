from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class IncompleteProductMasterRule:
    code: str = "INCOMPLETE_PRODUCT_MASTER"
    severity: Severity = Severity.ERROR
    description: str = "Product master must provide normal_price and cost for matched products."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.joined

        matched = frame["product_merge_state"] != "left_only"
        incomplete = matched & (frame["normal_price"].isna() | frame["cost"].isna())

        for row in frame.loc[incomplete].itertuples(index=False):
            is_normal_price_nan = pd.isna(row.normal_price)
            is_cost_nan = pd.isna(row.cost)

            if is_normal_price_nan and is_cost_nan:
                column = "product_code"
                observed = "normal_price=NaN, cost=NaN"
            elif is_normal_price_nan:
                column = "normal_price"
                observed = "normal_price=NaN"
            else:
                column = "cost"
                observed = "cost=NaN"

            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="상품 마스터 정보가 불완전합니다",
                    message="상품 마스터에 정상가 또는 원가가 기입되지 않았습니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=int(str(row.source_row)),
                    column=column,
                    entity=RowEntity(
                        promotion_id=str(row.promotion_id),
                        product_code=str(row.product_code),
                    ),
                    observed=observed,
                    expected="product_master must provide normal_price and cost",
                    suggestion="상품 마스터에 정상가와 원가를 입력하세요.",
                )
            )

        return issues


INCOMPLETE_PRODUCT_MASTER_RULE = IncompleteProductMasterRule()
