from __future__ import annotations

from dataclasses import dataclass

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class MissingProductMasterRule:
    code: str = "MISSING_PRODUCT_MASTER"
    severity: Severity = Severity.ERROR
    description: str = "Every promoted product must exist in the product master."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.joined
        missing = frame["product_merge_state"] == "left_only"
        for row in frame.loc[missing].itertuples(index=False):
            promotion_id = str(row.promotion_id)
            product_code = str(row.product_code)
            source_row = int(str(row.source_row))
            entity = RowEntity(
                promotion_id=promotion_id,
                product_code=product_code,
            )
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="상품 마스터를 찾을 수 없습니다",
                    message="프로모션 상품 코드가 상품 마스터에 없습니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=source_row,
                    column="product_code",
                    entity=entity,
                    related=None,
                    observed=product_code,
                    expected="product_master must contain the product_code",
                    suggestion="상품 마스터 파일에 해당 상품을 추가하세요.",
                )
            )
        return issues


MISSING_PRODUCT_MASTER_RULE = MissingProductMasterRule()
