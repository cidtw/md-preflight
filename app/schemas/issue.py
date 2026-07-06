from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueLocation(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    file: str
    row: int | None
    column: str | None


class ValidationIssue(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    code: str
    severity: Severity
    title: str
    message: str
    entity: dict[str, str]
    location: IssueLocation
    related_locations: list[IssueLocation] = Field(default_factory=list)
    observed: str | None
    expected: str | None
    suggestion: str | None
    rule_version: str = "1"
