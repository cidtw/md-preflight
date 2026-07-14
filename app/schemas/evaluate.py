"""HTTP request/response models for the evaluate API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.pipeline.types import ParameterValue, RecommendationResult


class EvaluateRequest(BaseModel):
    parameters: dict[str, ParameterValue] = Field(default_factory=dict)


class EvaluateResponse(RecommendationResult):
    """Alias for OpenAPI clarity; same shape as pipeline output."""
