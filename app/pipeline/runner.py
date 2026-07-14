"""Pipeline orchestrator: input → analyze → output (ROP adjust)."""

from __future__ import annotations

from collections.abc import Mapping

from app.pipeline.analyze.engine import analyze
from app.pipeline.input.template import get_template, validate_parameters
from app.pipeline.output.recommendation import render
from app.pipeline.types import InputTemplate, ParameterValue, RecommendationResult


def get_input_template() -> InputTemplate:
    return get_template()


def run(parameters: Mapping[str, ParameterValue]) -> RecommendationResult:
    """Execute the three-stage ROP pipeline deterministically."""
    validated = validate_parameters(parameters)
    calc = analyze(validated)
    return render(validated, calc)
