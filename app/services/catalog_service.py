"""Build the read-only preflight catalog from domain SSOT (T53)."""

from __future__ import annotations

from app.core.config import Settings
from app.domain.column_aliases import list_alias_examples
from app.domain.columns import ALL_SOURCE_COLUMNS, SourceFile
from app.rules import RULES
from app.schemas.catalog import (
    ColumnAliasEntry,
    PreflightCatalog,
    SourceColumnCatalog,
    ThresholdCatalog,
)

SOURCE_LABELS: dict[SourceFile, str] = {
    SourceFile.PROMOTION_PLAN: "프로모션 계획",
    SourceFile.PRODUCT_MASTER: "상품 마스터",
    SourceFile.INVENTORY: "재고",
}


def build_preflight_catalog(settings: Settings) -> PreflightCatalog:
    sources: list[SourceColumnCatalog] = []
    for source, columns in ALL_SOURCE_COLUMNS.items():
        entries = [
            ColumnAliasEntry(
                canonical=column,
                aliases=list_alias_examples(column, limit=8),
            )
            for column in columns
        ]
        sources.append(
            SourceColumnCatalog(
                source=source.value,
                label=SOURCE_LABELS.get(source, source.value),
                columns=entries,
            )
        )
    thresholds = settings.rule_thresholds
    return PreflightCatalog(
        thresholds=ThresholdCatalog(
            max_discount_rate=thresholds.max_discount_rate,
            min_margin_rate=thresholds.min_margin_rate,
        ),
        sources=sources,
        rules=[rule.meta() for rule in RULES],
        max_upload_bytes=settings.max_upload_bytes,
        allowed_extensions=list(settings.allowed_extensions),
    )
