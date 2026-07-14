from dataclasses import dataclass, field

import pandas as pd

from app.core.rule_config import RuleThresholds
from app.domain.columns import SourceFile


@dataclass(frozen=True, slots=True)
class HeaderMapping:
    """One original header → canonical column applied during ingest."""

    source_file: SourceFile
    original: str
    canonical: str


@dataclass(frozen=True, slots=True)
class PreflightContext:
    promotions: pd.DataFrame
    products: pd.DataFrame
    inventory: pd.DataFrame
    joined: pd.DataFrame
    thresholds: RuleThresholds
    column_mappings: tuple[HeaderMapping, ...] = field(default_factory=tuple)
