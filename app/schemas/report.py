from datetime import datetime
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.issue import ValidationIssue


class GenerationSource(StrEnum):
    LLM = "llm"
    FALLBACK = "fallback"


class PreflightSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    total_issues: int
    by_severity: dict[str, int]
    by_rule: dict[str, int]
    passed: bool
    checked_rows: int


class FileSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    file: str
    issue_count: int
    headline: str


class ChecklistItem(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    code: str
    file: str
    row: int | None
    column: str | None
    current: str | None
    suggested: str | None
    rationale: str


class ColumnMappingItem(BaseModel):
    """Audit record: uploaded header renamed to a rule-engine canonical key."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    file: str
    original: str
    canonical: str


class PreflightReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    run_id: str
    summary: PreflightSummary
    issues: list[ValidationIssue]
    ai_summary: str | None
    file_summaries: list[FileSummary] = Field(default_factory=list)
    checklist: list[str]
    checklist_items: list[ChecklistItem] = Field(default_factory=list)
    generated_by: GenerationSource
    failed_rules: list[str] = Field(default_factory=list)
    created_at: datetime
    rule_set_version: str
    column_mappings: list[ColumnMappingItem] = Field(default_factory=list)
