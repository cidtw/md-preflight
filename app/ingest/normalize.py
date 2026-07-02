from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from app.core.errors import IngestError
from app.core.rule_config import RuleThresholds
from app.domain.columns import (
    INVENTORY_COLUMNS,
    PRODUCT_MASTER_COLUMNS,
    PROMOTION_COLUMNS,
    SourceFile,
)
from app.domain.context import PreflightContext


def build_context(
    promotion_raw: pd.DataFrame,
    product_raw: pd.DataFrame,
    inventory_raw: pd.DataFrame,
    thresholds: RuleThresholds,
) -> PreflightContext:
    promotions = normalize_promotions(promotion_raw)
    products = normalize_product_master(product_raw)
    inventory = normalize_inventory(inventory_raw)
    products_for_join = products.drop(columns=["source_row"])
    inventory_for_join = inventory.drop(columns=["source_row"])
    joined = promotions.merge(
        products_for_join,
        on="product_code",
        how="left",
        indicator=True,
    ).rename(columns={"_merge": "product_merge_state"})
    joined = joined.merge(
        inventory_for_join,
        on="product_code",
        how="left",
        suffixes=("", "_inventory"),
    )
    return PreflightContext(
        promotions=promotions,
        products=products,
        inventory=inventory,
        joined=joined,
        thresholds=thresholds,
    )


def normalize_promotions(raw: pd.DataFrame) -> pd.DataFrame:
    frame = prepare_source_frame(raw, SourceFile.PROMOTION_PLAN, PROMOTION_COLUMNS)
    normalized = pd.DataFrame(
        {
            "promotion_id": to_text(frame["promotion_id"]),
            "product_code": to_text(frame["product_code"]),
            "start_date_raw": to_text(frame["start_date"]),
            "end_date_raw": to_text(frame["end_date"]),
            "promo_price_raw": to_text(frame["promo_price"]),
            "benefit_type": to_text(frame["benefit_type"]),
            "benefit_condition_raw": to_text(frame["benefit_condition"]),
        }
    )
    normalized["source_row"] = frame["source_row"]
    normalized["start_date"] = pd.to_datetime(frame["start_date"], errors="coerce")
    normalized["end_date"] = pd.to_datetime(frame["end_date"], errors="coerce")
    normalized["promo_price"] = pd.to_numeric(frame["promo_price"], errors="coerce")
    normalized["benefit_condition"] = to_text(frame["benefit_condition"])
    return normalized


def normalize_product_master(raw: pd.DataFrame) -> pd.DataFrame:
    frame = prepare_source_frame(raw, SourceFile.PRODUCT_MASTER, PRODUCT_MASTER_COLUMNS)
    normalized = pd.DataFrame(
        {
            "product_code": to_text(frame["product_code"]),
            "product_name": to_text(frame["product_name"]),
            "normal_price_raw": to_text(frame["normal_price"]),
            "cost_raw": to_text(frame["cost"]),
        }
    )
    normalized["source_row"] = frame["source_row"]
    normalized["normal_price"] = pd.to_numeric(frame["normal_price"], errors="coerce")
    normalized["cost"] = pd.to_numeric(frame["cost"], errors="coerce")
    return normalized


def normalize_inventory(raw: pd.DataFrame) -> pd.DataFrame:
    frame = prepare_source_frame(raw, SourceFile.INVENTORY, INVENTORY_COLUMNS)
    normalized = pd.DataFrame(
        {
            "product_code": to_text(frame["product_code"]),
            "stock_qty_raw": to_text(frame["stock_qty"]),
            "inbound_date_raw": to_text(frame["inbound_date"]),
            "expected_demand_raw": to_text(frame["expected_demand"]),
        }
    )
    normalized["source_row"] = frame["source_row"]
    normalized["stock_qty"] = pd.to_numeric(frame["stock_qty"], errors="coerce")
    normalized["inbound_date"] = pd.to_datetime(frame["inbound_date"], errors="coerce")
    normalized["expected_demand"] = pd.to_numeric(frame["expected_demand"], errors="coerce")
    return normalized


def prepare_source_frame(
    raw: pd.DataFrame,
    source_file: SourceFile,
    expected_columns: Iterable[str],
) -> pd.DataFrame:
    renamed = raw.copy()
    renamed.columns = [str(column).strip() for column in renamed.columns]
    missing = [column for column in expected_columns if column not in renamed.columns]
    if missing:
        msg = f"Missing columns in {source_file}: {', '.join(missing)}"
        raise IngestError(msg)
    frame = renamed.loc[:, list(expected_columns)].copy()
    frame["source_row"] = frame.index + 2
    return frame


def to_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()
