from __future__ import annotations

import pandas as pd

from app.core.rule_config import RuleThresholds
from app.domain.context import PreflightContext
from app.ingest.normalize import build_context
from app.rules.duplicate_master_code import DUPLICATE_MASTER_CODE_RULE


def test_duplicate_master_code_when_product_master_and_inventory_repeat_code() -> None:
    context = build_context(
        pd.DataFrame(
            [
                {
                    "promotion_id": "P-1",
                    "product_code": "SKU-1",
                    "start_date": "2026-07-10",
                    "end_date": "2026-07-12",
                    "promo_price": "7000",
                    "benefit_type": "discount",
                    "benefit_condition": "buy 2",
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    "product_code": "SKU-1",
                    "product_name": "Item 1",
                    "normal_price": "10000",
                    "cost": "5500",
                },
                {
                    "product_code": "SKU-1",
                    "product_name": "Item 1 duplicate",
                    "normal_price": "11000",
                    "cost": "5600",
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    "product_code": "SKU-1",
                    "stock_qty": "10",
                    "inbound_date": "2026-07-09",
                    "expected_demand": "8",
                },
                {
                    "product_code": "SKU-1",
                    "stock_qty": "9",
                    "inbound_date": "2026-07-10",
                    "expected_demand": "7",
                },
            ]
        ),
        RuleThresholds(),
    )

    issues = DUPLICATE_MASTER_CODE_RULE.apply(context)

    assert [(issue.location.file, issue.location.row) for issue in issues] == [
        ("product_master", 3),
        ("inventory", 3),
    ]
    assert all(issue.code == "DUPLICATE_MASTER_CODE" for issue in issues)
    assert all(issue.severity.value == "warning" for issue in issues)
    assert all(issue.location.column == "product_code" for issue in issues)
    assert all(issue.entity == {"promotion_id": "", "product_code": "SKU-1"} for issue in issues)


def test_duplicate_master_code_when_codes_unique() -> None:
    context = _build_unique_context()

    assert DUPLICATE_MASTER_CODE_RULE.apply(context) == []


def _build_unique_context() -> PreflightContext:
    return build_context(
        pd.DataFrame(
            [
                {
                    "promotion_id": "P-1",
                    "product_code": "SKU-1",
                    "start_date": "2026-07-10",
                    "end_date": "2026-07-12",
                    "promo_price": "7000",
                    "benefit_type": "discount",
                    "benefit_condition": "buy 2",
                },
                {
                    "promotion_id": "P-2",
                    "product_code": "SKU-2",
                    "start_date": "2026-07-11",
                    "end_date": "2026-07-13",
                    "promo_price": "8000",
                    "benefit_type": "discount",
                    "benefit_condition": "buy 1",
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    "product_code": "SKU-1",
                    "product_name": "Item 1",
                    "normal_price": "10000",
                    "cost": "5500",
                },
                {
                    "product_code": "SKU-2",
                    "product_name": "Item 2",
                    "normal_price": "11000",
                    "cost": "6000",
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    "product_code": "SKU-1",
                    "stock_qty": "10",
                    "inbound_date": "2026-07-09",
                    "expected_demand": "8",
                },
                {
                    "product_code": "SKU-2",
                    "stock_qty": "12",
                    "inbound_date": "2026-07-09",
                    "expected_demand": "7",
                },
            ]
        ),
        RuleThresholds(),
    )
