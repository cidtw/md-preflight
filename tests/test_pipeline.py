from __future__ import annotations

import pytest

from app.core.errors import InputValidationError
from app.pipeline import run
from app.pipeline.analyze.engine import analyze
from app.pipeline.input.template import validate_parameters
from app.pipeline.types import ParameterValue


def test_pipeline_is_deterministic() -> None:
    params: dict[str, ParameterValue] = {"quality": 80, "cost": 40, "risk": 30}
    a = run(params)
    b = run(params)
    assert a.model_dump() == b.model_dump()
    assert a.recommendation == b.recommendation


def test_pipeline_strong_band() -> None:
    result = run({"quality": 95, "cost": 10, "risk": 10})
    assert result.band == "strong"
    assert result.score >= 0.70
    assert "Recommend proceed" in result.recommendation


def test_pipeline_weak_band() -> None:
    result = run({"quality": 10, "cost": 90, "risk": 90})
    assert result.band == "weak"
    assert result.score < 0.40


def test_missing_required_parameter() -> None:
    with pytest.raises(InputValidationError, match="quality"):
        _ = validate_parameters({"cost": 10, "risk": 10})


def test_unknown_parameter_rejected() -> None:
    with pytest.raises(InputValidationError, match="Unknown"):
        _ = validate_parameters(
            {"quality": 50, "cost": 50, "risk": 50, "extra": 1},
        )


def test_out_of_range_rejected() -> None:
    with pytest.raises(InputValidationError, match="<="):
        _ = validate_parameters({"quality": 120, "cost": 10, "risk": 10})


def test_analyze_weights_sum_to_total() -> None:
    validated = validate_parameters({"quality": 100, "cost": 0, "risk": 0})
    analysis = analyze(validated)
    weighted_sum = sum(c.weighted_score for c in analysis.criteria)
    assert analysis.total_score == pytest.approx(weighted_sum)
    assert analysis.total_score == pytest.approx(1.0)
