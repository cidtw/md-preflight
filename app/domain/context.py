from dataclasses import dataclass

import pandas as pd

from app.core.rule_config import RuleThresholds


@dataclass(frozen=True, slots=True)
class PreflightContext:
    promotions: pd.DataFrame
    products: pd.DataFrame
    inventory: pd.DataFrame
    joined: pd.DataFrame
    thresholds: RuleThresholds
