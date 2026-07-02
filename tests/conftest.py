from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.core.rule_config import RuleThresholds
from app.domain.context import PreflightContext
from app.ingest.loader import load_table
from app.ingest.normalize import build_context


@pytest.fixture()
def thresholds() -> RuleThresholds:
    return RuleThresholds()


@pytest.fixture()
def sample_context(thresholds: RuleThresholds) -> PreflightContext:
    promotion = pd.DataFrame(
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
                "start_date": "2026-07-15",
                "end_date": "2026-07-10",
                "promo_price": "12000",
                "benefit_type": "discount",
                "benefit_condition": "buy 1",
            },
            {
                "promotion_id": "P-3",
                "product_code": "SKU-3",
                "start_date": "2026-07-10",
                "end_date": "2026-07-15",
                "promo_price": "2000",
                "benefit_type": "discount",
                "benefit_condition": "buy 1",
            },
            {
                "promotion_id": "P-4",
                "product_code": "SKU-9",
                "start_date": "2026-07-10",
                "end_date": "2026-07-15",
                "promo_price": "5000",
                "benefit_type": "discount",
                "benefit_condition": "buy 1",
            },
        ]
    )
    products = pd.DataFrame(
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
                "normal_price": "10000",
                "cost": "5500",
            },
            {
                "product_code": "SKU-3",
                "product_name": "Item 3",
                "normal_price": "10000",
                "cost": "5500",
            },
        ]
    )
    inventory = pd.DataFrame(
        [
            {
                "product_code": "SKU-1",
                "stock_qty": "10",
                "inbound_date": "2026-07-09",
                "expected_demand": "8",
            },
            {
                "product_code": "SKU-2",
                "stock_qty": "10",
                "inbound_date": "2026-07-09",
                "expected_demand": "8",
            },
            {
                "product_code": "SKU-3",
                "stock_qty": "10",
                "inbound_date": "2026-07-09",
                "expected_demand": "8",
            },
        ]
    )
    return build_context(promotion, products, inventory, thresholds)


@pytest.fixture()
def sample_files_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "samples"


@pytest.fixture()
def clean_context(thresholds: RuleThresholds, sample_files_dir: Path) -> PreflightContext:
    base = sample_files_dir / "clean"
    return build_context(
        load_table(str(base / "promotion_plan.xlsx"), (base / "promotion_plan.xlsx").read_bytes()),
        load_table(str(base / "product_master.xlsx"), (base / "product_master.xlsx").read_bytes()),
        load_table(str(base / "inventory.xlsx"), (base / "inventory.xlsx").read_bytes()),
        thresholds,
    )
