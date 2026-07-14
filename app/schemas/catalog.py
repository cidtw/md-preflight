"""Read-only service catalog for Settings UI (T53)."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rule_meta import RuleMeta


class ColumnAliasEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    canonical: str
    aliases: list[str] = Field(default_factory=list)


class SourceColumnCatalog(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    source: str
    label: str
    columns: list[ColumnAliasEntry] = Field(default_factory=list)


class ThresholdCatalog(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    max_discount_rate: float
    min_margin_rate: float


class PreflightCatalog(BaseModel):
    """Server SSOT snapshot for settings / education screens."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    thresholds: ThresholdCatalog
    sources: list[SourceColumnCatalog] = Field(default_factory=list)
    rules: list[RuleMeta] = Field(default_factory=list)
    max_upload_bytes: int
    allowed_extensions: list[str] = Field(default_factory=list)
