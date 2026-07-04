from __future__ import annotations

from collections.abc import Hashable
from typing import Literal

import pandas as pd
import pytest

from app.core.errors import IngestError
from app.core.rule_config import RuleThresholds
from app.ingest.normalize import build_context
from app.rules.promo_price import INVALID_PROMO_PRICE_RULE


def build_promotions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "promotion_id": "P-1",
                "product_code": "SKU-1",
                "start_date": "2026-07-10",
                "end_date": "2026-07-12",
                "promo_price": "12000",
                "benefit_type": "discount",
                "benefit_condition": "buy 1",
            },
        ]
    )


def build_products() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_code": "SKU-1",
                "product_name": "Item 1 primary",
                "normal_price": "10000",
                "cost": "5500",
            },
        ]
    )


def build_inventory() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_code": "SKU-1",
                "stock_qty": "10",
                "inbound_date": "2026-07-09",
                "expected_demand": "8",
            },
        ]
    )


def test_build_context_dedups_product_join_inputs_without_mutating_raw_frames() -> None:
    products = pd.concat([build_products(), build_products()], ignore_index=True)

    context = build_context(
        build_promotions(),
        products,
        build_inventory(),
        RuleThresholds(),
    )

    assert len(context.promotions) == 1
    assert len(context.joined) == 1
    assert len(context.products) == 2


def test_duplicate_product_master_rows_do_not_duplicate_promo_price_issues() -> None:
    products = pd.concat([build_products(), build_products()], ignore_index=True)

    context = build_context(
        build_promotions(),
        products,
        build_inventory(),
        RuleThresholds(),
    )

    issues = INVALID_PROMO_PRICE_RULE.apply(context)

    assert len(issues) == 1
    assert issues[0].entity == {"promotion_id": "P-1", "product_code": "SKU-1"}


def test_build_context_dedups_inventory_join_inputs_without_mutating_raw_frames() -> None:
    inventory = pd.concat([build_inventory(), build_inventory()], ignore_index=True)

    context = build_context(
        build_promotions(),
        build_products(),
        inventory,
        RuleThresholds(),
    )

    assert len(context.promotions) == 1
    assert len(context.joined) == 1
    assert len(context.inventory) == 2


def test_build_context_raises_when_join_invariant_is_violated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_drop_duplicates = pd.DataFrame.drop_duplicates

    def drop_duplicates_without_product_code_dedup(
        self: pd.DataFrame,
        subset: Hashable | list[Hashable] | None = None,
        *,
        keep: Literal["first", "last", False] = "first",
        inplace: Literal[False] = False,
        ignore_index: bool = False,
    ) -> pd.DataFrame:
        if subset == "product_code":
            return self.copy()
        return original_drop_duplicates(
            self,
            subset=subset,
            keep=keep,
            inplace=inplace,
            ignore_index=ignore_index,
        )

    monkeypatch.setattr(
        pd.DataFrame,
        "drop_duplicates",
        drop_duplicates_without_product_code_dedup,
    )

    with pytest.raises(IngestError, match="join invariant violated"):
        _ = build_context(
            build_promotions(),
            pd.concat([build_products(), build_products()], ignore_index=True),
            build_inventory(),
            RuleThresholds(),
        )
