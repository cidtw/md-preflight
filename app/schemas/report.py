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


class PreflightReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    run_id: str
    summary: PreflightSummary
    issues: list[ValidationIssue]
    ai_summary: str | None
    checklist: list[str]
    generated_by: GenerationSource
    failed_rules: list[str] = Field(default_factory=list)
