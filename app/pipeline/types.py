"""Shared contracts between pipeline stages (input -> analyze -> output)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Band = Literal["strong", "moderate", "weak"]
ParamType = Literal["number", "string", "boolean"]
ParameterValue = str | int | float | bool


class ParameterSpec(BaseModel):
    """One field in the public input template."""

    key: str
    label: str
    type: ParamType
    required: bool = True
    description: str = ""
    minimum: float | None = None
    maximum: float | None = None
    allowed_values: list[str] | None = None


class InputTemplate(BaseModel):
    """Discoverable template: clients only need keys listed here."""

    id: str
    title: str
    description: str
    version: str
    parameters: list[ParameterSpec]


class ValidatedInput(BaseModel):
    """Output of the input stage - normalized parameters only."""

    template_id: str
    template_version: str
    parameters: dict[str, ParameterValue]


class CriterionScore(BaseModel):
    criterion_id: str
    label: str
    weight: float
    raw_score: float = Field(ge=0.0, le=1.0)
    weighted_score: float
    rationale: str = ""


class AnalysisResult(BaseModel):
    total_score: float = Field(ge=0.0, le=1.0)
    band: Band
    criteria: list[CriterionScore]


class RecommendationResult(BaseModel):
    """Final pipeline payload: one-line recommendation + structured details."""

    recommendation: str
    score: float
    band: Band
    template_id: str
    template_version: str
    details: AnalysisResult
