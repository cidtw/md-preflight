"""Canonical column names + real-world header aliases.

Alpha build required exact English headers. Midterm feedback asked for
resilience when ERP / franchise HQ exports use Korean or synonym headers.
Aliases collapse to the canonical names used by rules and joins.
"""

from __future__ import annotations

import re
from typing import Final

from app.domain.columns import (
    INVENTORY_COLUMNS,
    PRODUCT_MASTER_COLUMNS,
    PROMOTION_COLUMNS,
    SourceFile,
)

# Token-ish normalize: lower, strip, collapse separators so
# "Product Code", "product_code", "product-code", "상품 코드" can match.
_SEP_RE = re.compile(r"[\s_\-./]+")


def normalize_header_key(value: str) -> str:
    text = str(value).strip().lower()
    text = _SEP_RE.sub("", text)
    return text


# Each canonical key maps to a set of normalized alias keys (including itself).
# Keep lists explicit and reviewable — no fuzzy ML.
_ALIAS_GROUPS: Final[dict[str, tuple[str, ...]]] = {
    "promotion_id": (
        "promotion_id",
        "promotionid",
        "promo_id",
        "promoid",
        "event_id",
        "eventid",
        "행사id",
        "행사코드",
        "프로모션id",
        "프로모션코드",
        "행사번호",
    ),
    "product_code": (
        "product_code",
        "productcode",
        "product_id",
        "productid",
        "sku",
        "item_code",
        "itemcode",
        "item_id",
        "itemid",
        "상품코드",
        "품번",
        "상품번호",
        "제품코드",
        "자재코드",
    ),
    "start_date": (
        "start_date",
        "startdate",
        "promo_start",
        "promostart",
        "from_date",
        "fromdate",
        "시작일",
        "시작일자",
        "행사시작일",
        "프로모션시작일",
    ),
    "end_date": (
        "end_date",
        "enddate",
        "promo_end",
        "promoend",
        "to_date",
        "todate",
        "종료일",
        "종료일자",
        "행사종료일",
        "프로모션종료일",
    ),
    "promo_price": (
        "promo_price",
        "promoprice",
        "promotion_price",
        "promotionprice",
        "sale_price",
        "saleprice",
        "event_price",
        "eventprice",
        "행사가",
        "할인가",
        "프로모션가",
        "특매가",
    ),
    "benefit_type": (
        "benefit_type",
        "benefittype",
        "promo_type",
        "promotype",
        "증정유형",
        "혜택유형",
        "혜택구분",
        "사은품유형",
    ),
    "benefit_condition": (
        "benefit_condition",
        "benefitcondition",
        "promo_condition",
        "promocondition",
        "증정조건",
        "혜택조건",
        "사은품조건",
    ),
    "product_name": (
        "product_name",
        "productname",
        "item_name",
        "itemname",
        "name",
        "상품명",
        "제품명",
        "품명",
    ),
    "normal_price": (
        "normal_price",
        "normalprice",
        "list_price",
        "listprice",
        "regular_price",
        "regularprice",
        "retail_price",
        "retailprice",
        "정상가",
        "정가",
        "판매가",
        "소비자가",
    ),
    "cost": (
        "cost",
        "unit_cost",
        "unitcost",
        "cogs",
        "원가",
        "매입가",
        "공급가",
        "입고가",
    ),
    "stock_qty": (
        "stock_qty",
        "stockqty",
        "stock",
        "quantity",
        "qty",
        "on_hand",
        "onhand",
        "재고",
        "재고수량",
        "현재고",
        "보유수량",
    ),
    "inbound_date": (
        "inbound_date",
        "inbounddate",
        "arrival_date",
        "arrivaldate",
        "receive_date",
        "receivedate",
        "입고일",
        "입고일자",
        "입고예정일",
        "입고예정일자",
    ),
    "expected_demand": (
        "expected_demand",
        "expecteddemand",
        "forecast",
        "forecast_qty",
        "forecastqty",
        "expected_sales",
        "expectedsales",
        "예상수요",
        "예상판매",
        "예상판매량",
        "예상수량",
    ),
}

# Pre-compute: normalized alias → canonical
_ALIAS_TO_CANONICAL: Final[dict[str, str]] = {}
for _canonical, _aliases in _ALIAS_GROUPS.items():
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[normalize_header_key(_alias)] = _canonical
    _ALIAS_TO_CANONICAL[normalize_header_key(_canonical)] = _canonical

SOURCE_CANONICAL_COLUMNS: Final[dict[SourceFile, tuple[str, ...]]] = {
    SourceFile.PROMOTION_PLAN: PROMOTION_COLUMNS,
    SourceFile.PRODUCT_MASTER: PRODUCT_MASTER_COLUMNS,
    SourceFile.INVENTORY: INVENTORY_COLUMNS,
}


def resolve_canonical_name(header: str) -> str | None:
    """Return canonical column name if header matches a known alias."""
    return _ALIAS_TO_CANONICAL.get(normalize_header_key(header))


def build_column_rename_map(
    headers: list[str],
    expected_columns: tuple[str, ...] | list[str],
) -> tuple[dict[str, str], list[str]]:
    """Map original headers → canonical names for expected columns only.

    Returns (rename_map, missing_canonical).
    - First matching alias wins per canonical key (left-to-right header order).
    - Headers that do not map to an expected canonical stay untouched (dropped later).
    """
    expected = set(expected_columns)
    rename_map: dict[str, str] = {}
    claimed: set[str] = set()

    for header in headers:
        raw = str(header).strip()
        if not raw:
            continue
        # Exact match first (preserve case-stripped identity)
        if raw in expected and raw not in claimed:
            if raw != header:
                rename_map[header] = raw
            claimed.add(raw)
            continue
        stripped = raw  # already strip
        if stripped in expected and stripped not in claimed and stripped != header:
            rename_map[header] = stripped
            claimed.add(stripped)
            continue
        # Case-insensitive exact on canonical English names
        lower_hit = next(
            (
                column
                for column in expected
                if column.lower() == stripped.lower() and column not in claimed
            ),
            None,
        )
        if lower_hit is not None:
            if header != lower_hit:
                rename_map[header] = lower_hit
            claimed.add(lower_hit)
            continue
        canonical = resolve_canonical_name(header)
        if canonical is None or canonical not in expected or canonical in claimed:
            continue
        if header != canonical:
            rename_map[header] = canonical
        claimed.add(canonical)

    missing = [column for column in expected_columns if column not in claimed]
    return rename_map, missing


def suggest_headers_for_missing(
    missing: list[str],
    actual_headers: list[str],
    *,
    limit: int = 3,
) -> dict[str, list[str]]:
    """For each missing canonical, list actual headers that almost match (same normalize)."""
    suggestions: dict[str, list[str]] = {}
    actual_norm = {normalize_header_key(h): h for h in actual_headers if str(h).strip()}
    for column in missing:
        # Show known aliases that appear as substrings in actual headers (light hint)
        aliases = _ALIAS_GROUPS.get(column, (column,))
        hits: list[str] = []
        for alias in aliases:
            key = normalize_header_key(alias)
            if key in actual_norm:
                hits.append(str(actual_norm[key]))
        # Also: any actual header whose normalize contains the canonical token
        canon_key = normalize_header_key(column)
        for norm, original in actual_norm.items():
            if canon_key and (canon_key in norm or norm in canon_key) and original not in hits:
                hits.append(str(original))
        if hits:
            suggestions[column] = hits[:limit]
    return suggestions
