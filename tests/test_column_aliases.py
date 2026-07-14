from __future__ import annotations

import pandas as pd
import pytest

from app.core.errors import IngestError
from app.domain.column_aliases import (
    build_column_rename_map,
    normalize_header_key,
    resolve_canonical_name,
)
from app.domain.columns import PRODUCT_MASTER_COLUMNS, PROMOTION_COLUMNS
from app.ingest.normalize import (
    normalize_inventory,
    normalize_product_master,
    normalize_promotions,
)


def test_normalize_header_key_collapses_separators() -> None:
    assert normalize_header_key("Product Code") == "productcode"
    assert normalize_header_key("product_code") == "productcode"
    assert normalize_header_key("  상품 코드 ") == "상품코드"


def test_resolve_canonical_name_korean_and_english() -> None:
    assert resolve_canonical_name("상품코드") == "product_code"
    assert resolve_canonical_name("행사가") == "promo_price"
    assert resolve_canonical_name("재고수량") == "stock_qty"
    assert resolve_canonical_name("SKU") == "product_code"
    assert resolve_canonical_name("unknown_xyz") is None


def test_build_column_rename_map_korean_promotion_headers() -> None:
    headers = [
        "행사코드",
        "상품코드",
        "시작일",
        "종료일",
        "행사가",
        "혜택유형",
        "혜택조건",
    ]
    rename, missing = build_column_rename_map(headers, PROMOTION_COLUMNS)
    assert missing == []
    assert rename["행사코드"] == "promotion_id"
    assert rename["상품코드"] == "product_code"
    assert rename["시작일"] == "start_date"
    assert rename["행사가"] == "promo_price"


def test_build_column_rename_map_keeps_exact_english() -> None:
    headers = list(PRODUCT_MASTER_COLUMNS)
    rename, missing = build_column_rename_map(headers, PRODUCT_MASTER_COLUMNS)
    assert missing == []
    assert rename == {}


def test_build_column_rename_map_case_insensitive_english() -> None:
    headers = ["Product_Code", "Product_Name", "Normal_Price", "Cost"]
    rename, missing = build_column_rename_map(headers, PRODUCT_MASTER_COLUMNS)
    assert missing == []
    assert rename["Product_Code"] == "product_code"
    assert rename["Normal_Price"] == "normal_price"


def test_normalize_promotions_accepts_korean_headers() -> None:
    raw = pd.DataFrame(
        {
            "행사코드": ["P1"],
            "상품코드": ["A1"],
            "시작일": ["2026-07-01"],
            "종료일": ["2026-07-10"],
            "행사가": [900],
            "혜택유형": [""],
            "혜택조건": [""],
        }
    )
    frame, mappings = normalize_promotions(raw)
    assert list(frame["product_code"]) == ["A1"]
    assert frame["promo_price"].iloc[0] == 900
    assert frame["source_row"].iloc[0] == 2
    assert any(m.canonical == "product_code" for m in mappings)


def test_normalize_product_master_accepts_synonyms() -> None:
    raw = pd.DataFrame(
        {
            "SKU": ["A1"],
            "품명": ["테스트"],
            "정상가": [1000],
            "원가": [600],
        }
    )
    frame, mappings = normalize_product_master(raw)
    assert list(frame["product_code"]) == ["A1"]
    assert list(frame["product_name"]) == ["테스트"]
    assert frame["normal_price"].iloc[0] == 1000
    originals = {m.original for m in mappings}
    assert "SKU" in originals or "품명" in originals


def test_normalize_inventory_accepts_korean_headers() -> None:
    raw = pd.DataFrame(
        {
            "상품코드": ["A1"],
            "재고수량": [10],
            "입고예정일": ["2026-06-01"],
            "예상수요": [5],
        }
    )
    frame, mappings = normalize_inventory(raw)
    assert frame["stock_qty"].iloc[0] == 10
    assert frame["expected_demand"].iloc[0] == 5
    assert len(mappings) >= 3


def test_prepare_source_frame_missing_still_errors_with_hint() -> None:
    raw = pd.DataFrame({"상품코드": ["A1"], "재고수량": [1]})
    with pytest.raises(IngestError) as exc:
        _ = normalize_inventory(raw)
    message = str(exc.value)
    assert "Missing columns" in message
    assert "inbound_date" in message
    assert "expected_demand" in message
    # T52: alias examples when file has no near-match headers
    assert "similar headers" in message
    assert "예:" in message or "←" in message
