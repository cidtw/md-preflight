from __future__ import annotations

import pandas as pd

from app.core.rule_config import RuleThresholds
from app.domain.context import PreflightContext
from app.rules.date_range import INVALID_DATE_RANGE_RULE
from app.rules.discount_rate import EXTREME_DISCOUNT_RATE_RULE
from app.rules.product_master import MISSING_PRODUCT_MASTER_RULE
from app.rules.promo_price import INVALID_PROMO_PRICE_RULE


def test_invalid_date_range_when_start_after_end(
    sample_context: PreflightContext,
) -> None:
    issues = INVALID_DATE_RANGE_RULE.apply(sample_context)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "INVALID_DATE_RANGE"
    assert issue.severity.value == "error"
    assert issue.location.row == 3
    assert issue.entity == {"promotion_id": "P-2", "product_code": "SKU-2"}
    assert issue.observed == "start=2026-07-15, end=2026-07-10"
    assert issue.suggestion is not None


def test_missing_product_master_when_product_not_found(
    sample_context: PreflightContext,
) -> None:
    issues = MISSING_PRODUCT_MASTER_RULE.apply(sample_context)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "MISSING_PRODUCT_MASTER"
    assert issue.severity.value == "error"
    assert issue.location.row == 5
    assert issue.entity == {"promotion_id": "P-4", "product_code": "SKU-9"}
    assert issue.observed == "SKU-9"
    assert issue.suggestion is not None


def test_invalid_promo_price_when_zero_price(sample_context: PreflightContext) -> None:
    issues = INVALID_PROMO_PRICE_RULE.apply(sample_context)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "INVALID_PROMO_PRICE"
    assert issue.severity.value == "error"
    assert issue.location.row == 3
    assert issue.entity == {"promotion_id": "P-2", "product_code": "SKU-2"}
    assert issue.observed == "promo_price=12000"
    assert issue.suggestion is not None


def test_extreme_discount_rate_when_discount_above_threshold(
    sample_context: PreflightContext,
) -> None:
    issues = EXTREME_DISCOUNT_RATE_RULE.apply(sample_context)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "EXTREME_DISCOUNT_RATE"
    assert issue.severity.value == "warning"
    assert issue.location.row == 4
    assert issue.entity == {"promotion_id": "P-3", "product_code": "SKU-3"}
    assert issue.observed == "discount_rate=80.00%"
    assert issue.suggestion is not None


def test_missing_product_master_does_not_flag_null_normal_price() -> None:
    promotion = pd.DataFrame(
        [
            {
                "promotion_id": "P-10",
                "product_code": "SKU-10",
                "start_date": "2026-07-10",
                "end_date": "2026-07-12",
                "promo_price": "7000",
                "benefit_type": "discount",
                "benefit_condition": "buy 2",
            },
        ]
    )
    products = pd.DataFrame(
        [
            {
                "product_code": "SKU-10",
                "product_name": "Null Price Item",
                "normal_price": None,
                "cost": "5500",
            },
        ]
    )
    inventory = pd.DataFrame(
        [
            {
                "product_code": "SKU-10",
                "stock_qty": "10",
                "inbound_date": "2026-07-09",
                "expected_demand": "8",
            },
        ]
    )
    context = PreflightContext(
        promotions=promotion,
        products=products,
        inventory=inventory,
        joined=pd.DataFrame(
            [
                {
                    "promotion_id": "P-10",
                    "product_code": "SKU-10",
                    "start_date_raw": "2026-07-10",
                    "end_date_raw": "2026-07-12",
                    "promo_price_raw": "7000",
                    "benefit_type": "discount",
                    "benefit_condition_raw": "buy 2",
                    "source_row": 2,
                    "start_date": pd.Timestamp("2026-07-10"),
                    "end_date": pd.Timestamp("2026-07-12"),
                    "promo_price": 7000.0,
                    "benefit_condition": "buy 2",
                    "product_name": "Null Price Item",
                    "normal_price_raw": None,
                    "cost_raw": "5500",
                    "normal_price": None,
                    "cost": 5500.0,
                    "product_merge_state": "both",
                    "stock_qty_raw": "10",
                    "inbound_date_raw": "2026-07-09",
                    "expected_demand_raw": "8",
                    "stock_qty": 10.0,
                    "inbound_date": pd.Timestamp("2026-07-09"),
                    "expected_demand": 8.0,
                },
            ]
        ),
        thresholds=RuleThresholds(),
    )
    assert MISSING_PRODUCT_MASTER_RULE.apply(context) == []


def test_clean_sample_has_no_issues(clean_context: PreflightContext) -> None:
    issues = INVALID_DATE_RANGE_RULE.apply(clean_context)
    issues += MISSING_PRODUCT_MASTER_RULE.apply(clean_context)
    issues += INVALID_PROMO_PRICE_RULE.apply(clean_context)
    issues += EXTREME_DISCOUNT_RATE_RULE.apply(clean_context)
    assert issues == []
