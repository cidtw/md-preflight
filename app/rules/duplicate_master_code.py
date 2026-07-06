from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.rules.base import RowEntity, make_issue
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.rule_meta import RuleMeta


@dataclass(frozen=True, slots=True)
class DuplicateMasterCodeRule:
    code: str = "DUPLICATE_MASTER_CODE"
    severity: Severity = Severity.WARNING
    description: str = "Product master and inventory must not contain duplicate product codes."

    def meta(self) -> RuleMeta:
        return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    def apply(self, ctx: PreflightContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # 1. products 중복 검사
        products_dups = ctx.products[ctx.products["product_code"].duplicated(keep=False)]
        for code, group in products_dups.groupby("product_code"):
            row = group.iloc[1]
            source_row_val = cast(object, row["source_row"])
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="상품 마스터에 중복된 상품 코드가 존재합니다",
                    message=f"상품 마스터에 동일한 상품 코드({code})가 여러 번 정의되어 있습니다.",
                    file=SourceFile.PRODUCT_MASTER.value,
                    row=int(str(source_row_val)),
                    column="product_code",
                    entity=RowEntity(
                        promotion_id="",
                        product_code=str(code),
                    ),
                    related=None,
                    observed=f"duplicate_count={len(group)}",
                    expected="Each product_code must be unique in product_master",
                    suggestion="상품 마스터에서 중복 기재된 상품 행을 제거하거나 수정하세요.",
                )
            )

        # 2. inventory 중복 검사
        inventory_dups = ctx.inventory[ctx.inventory["product_code"].duplicated(keep=False)]
        for code, group in inventory_dups.groupby("product_code"):
            row = group.iloc[1]
            source_row_val = cast(object, row["source_row"])
            issues.append(
                make_issue(
                    code=self.code,
                    severity=self.severity,
                    title="재고 마스터에 중복된 상품 코드가 존재합니다",
                    message=f"재고 마스터에 동일한 상품 코드({code})가 여러 번 정의되어 있습니다.",
                    file=SourceFile.INVENTORY.value,
                    row=int(str(source_row_val)),
                    column="product_code",
                    entity=RowEntity(
                        promotion_id="",
                        product_code=str(code),
                    ),
                    related=None,
                    observed=f"duplicate_count={len(group)}",
                    expected="Each product_code must be unique in inventory",
                    suggestion="재고 마스터에서 중복 기재된 재고 행을 제거하거나 수정하세요.",
                )
            )

        return issues


DUPLICATE_MASTER_CODE_RULE = DuplicateMasterCodeRule()
