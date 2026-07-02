from enum import StrEnum
from typing import Final


class SourceFile(StrEnum):
    PROMOTION_PLAN = "promotion_plan"
    PRODUCT_MASTER = "product_master"
    INVENTORY = "inventory"


PROMOTION_COLUMNS: Final[tuple[str, ...]] = (
    "promotion_id",
    "product_code",
    "start_date",
    "end_date",
    "promo_price",
    "benefit_type",
    "benefit_condition",
)
PRODUCT_MASTER_COLUMNS: Final[tuple[str, ...]] = (
    "product_code",
    "product_name",
    "normal_price",
    "cost",
)
INVENTORY_COLUMNS: Final[tuple[str, ...]] = (
    "product_code",
    "stock_qty",
    "inbound_date",
    "expected_demand",
)
ALL_SOURCE_COLUMNS: Final[dict[SourceFile, tuple[str, ...]]] = {
    SourceFile.PROMOTION_PLAN: PROMOTION_COLUMNS,
    SourceFile.PRODUCT_MASTER: PRODUCT_MASTER_COLUMNS,
    SourceFile.INVENTORY: INVENTORY_COLUMNS,
}
