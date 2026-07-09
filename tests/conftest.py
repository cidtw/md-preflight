from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pandas as pd
import pytest

from app.api import deps as api_deps
from app.core.rule_config import RuleThresholds
from app.domain.context import PreflightContext
from app.ingest.loader import load_table
from app.ingest.normalize import build_context
from app.services.history_store import InMemoryHistoryStore


@pytest.fixture()
def thresholds() -> RuleThresholds:
    return RuleThresholds()


def build_sample_promotions() -> pd.DataFrame:
    return pd.DataFrame(
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
            {
                "promotion_id": "P-5",
                "product_code": "SKU-5",
                "start_date": "2026-07-10",
                "end_date": "2026-07-13",
                "promo_price": "5600",
                "benefit_type": "discount",
                "benefit_condition": "buy 3",
            },
            {
                "promotion_id": "P-6",
                "product_code": "SKU-6",
                "start_date": "2026-07-11",
                "end_date": "2026-07-16",
                "promo_price": "6500",
                "benefit_type": "gift",
                "benefit_condition": "",
            },
        ]
    )


def build_sample_products() -> pd.DataFrame:
    return pd.DataFrame(
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
            {
                "product_code": "SKU-5",
                "product_name": "Item 5",
                "normal_price": "10000",
                "cost": "5500",
            },
            {
                "product_code": "SKU-6",
                "product_name": "Item 6",
                "normal_price": "10000",
                "cost": "5000",
            },
        ]
    )


def build_sample_inventory() -> pd.DataFrame:
    return pd.DataFrame(
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
            {
                "product_code": "SKU-5",
                "stock_qty": "5",
                "inbound_date": "2026-07-12",
                "expected_demand": "8",
            },
            {
                "product_code": "SKU-6",
                "stock_qty": "15",
                "inbound_date": "2026-07-09",
                "expected_demand": "7",
            },
            {
                "product_code": "SKU-9",
                "stock_qty": "5",
                "inbound_date": "2026-07-09",
                "expected_demand": "4",
            },
        ]
    )


@pytest.fixture()
def sample_context(thresholds: RuleThresholds) -> PreflightContext:
    return build_context(
        build_sample_promotions(),
        build_sample_products(),
        build_sample_inventory(),
        thresholds,
    )


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


@pytest.fixture(autouse=True)
def isolate_history_store(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "")
    monkeypatch.setenv("CLERK_SECRET_KEY", "")
    monkeypatch.setenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")
    # Most existing tests simulate a signed-in user via the X-MD-Preflight-User-Id
    # stub header. Tests that specifically exercise the "stub disabled" path
    # (auth_mode == "off") must override this back to "" themselves.
    monkeypatch.setenv("MDPREFLIGHT_ALLOW_STUB_AUTH", "true")
    monkeypatch.setattr(api_deps, "history_store_instance", InMemoryHistoryStore())
    monkeypatch.setattr(api_deps, "_history_store_initialized", True)
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
