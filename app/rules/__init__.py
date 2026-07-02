from app.rules.base import Rule
from app.rules.date_range import INVALID_DATE_RANGE_RULE
from app.rules.discount_rate import EXTREME_DISCOUNT_RATE_RULE
from app.rules.product_master import MISSING_PRODUCT_MASTER_RULE
from app.rules.promo_price import INVALID_PROMO_PRICE_RULE

RULES: list[Rule] = [
    INVALID_DATE_RANGE_RULE,
    MISSING_PRODUCT_MASTER_RULE,
    INVALID_PROMO_PRICE_RULE,
    EXTREME_DISCOUNT_RATE_RULE,
]
