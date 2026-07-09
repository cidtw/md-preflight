import hashlib
import json
from collections.abc import Sequence

from app.core.rule_config import RuleThresholds
from app.rules.base import Rule
from app.rules.benefit_condition import MISSING_BENEFIT_CONDITION_RULE
from app.rules.date_range import INVALID_DATE_RANGE_RULE
from app.rules.discount_rate import EXTREME_DISCOUNT_RATE_RULE
from app.rules.duplicate_master_code import DUPLICATE_MASTER_CODE_RULE
from app.rules.inbound_date import INBOUND_DATE_CONFLICT_RULE
from app.rules.incomplete_master import INCOMPLETE_PRODUCT_MASTER_RULE
from app.rules.inventory import INVENTORY_SHORTAGE_RISK_RULE
from app.rules.margin_rate import LOW_MARGIN_RATE_RULE
from app.rules.product_master import MISSING_PRODUCT_MASTER_RULE
from app.rules.promo_price import INVALID_PROMO_PRICE_RULE

RULES: list[Rule] = [
    INVALID_DATE_RANGE_RULE,
    MISSING_PRODUCT_MASTER_RULE,
    INCOMPLETE_PRODUCT_MASTER_RULE,
    INVALID_PROMO_PRICE_RULE,
    EXTREME_DISCOUNT_RATE_RULE,
    LOW_MARGIN_RATE_RULE,
    DUPLICATE_MASTER_CODE_RULE,
    INVENTORY_SHORTAGE_RISK_RULE,
    INBOUND_DATE_CONFLICT_RULE,
    MISSING_BENEFIT_CONDITION_RULE,
]


def compute_rule_set_version(
    thresholds: RuleThresholds,
    *,
    rules: Sequence[Rule] = RULES,
) -> str:
    """Deterministic fingerprint of which rules + thresholds produced a report.

    Same rule codes + same threshold values -> same version, so two reports can
    be compared to know whether they were judged by the same rule configuration.
    """
    payload = {
        "codes": sorted(rule.code for rule in rules),
        "thresholds": thresholds.model_dump(mode="json"),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return digest[:12]
