from __future__ import annotations

from dataclasses import dataclass

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class MissingBenefitConditionRule:
    code: str = "MISSING_BENEFIT_CONDITION"
    severity: Severity = Severity.ERROR
    description: str = "Benefit condition must exist when a benefit type is provided."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        frame = ctx.promotions
        invalid = (
            frame["benefit_type"].notna()
            & (frame["benefit_type"] != "")
            & (frame["benefit_condition"].isna() | (frame["benefit_condition"] == ""))
        )
        for row in frame.loc[invalid].itertuples(index=False):
            benefit_type = str(row.benefit_type)
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="혜택 조건이 비어 있습니다",
                    message="혜택 유형이 지정된 프로모션에는 상세 조건이 필요합니다.",
                    file=SourceFile.PROMOTION_PLAN.value,
                    row=int(str(row.source_row)),
                    column="benefit_condition",
                    entity=RowEntity(
                        promotion_id=str(row.promotion_id),
                        product_code=str(row.product_code),
                    ),
                    related=None,
                    observed=f"benefit_type={benefit_type}, benefit_condition=<empty>",
                    expected="benefit_condition must be provided when benefit_type is set",
                    suggestion="혜택 조건을 입력하거나 혜택 유형을 제거하세요.",
                )
            )
        return issues


MISSING_BENEFIT_CONDITION_RULE = MissingBenefitConditionRule()
