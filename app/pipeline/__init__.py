"""Modular pipeline: input → analyze → output (store-specific ROP)."""

from app.pipeline.runner import get_input_template, run
from app.pipeline.types import InputTemplate, RecommendationResult

__all__ = [
    "InputTemplate",
    "RecommendationResult",
    "get_input_template",
    "run",
]
