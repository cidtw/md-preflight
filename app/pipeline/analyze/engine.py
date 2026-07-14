"""Stage 2 — deterministic weighted analysis."""

from __future__ import annotations

from app.pipeline.analyze.weights import CriterionDef, active_criteria
from app.pipeline.types import AnalysisResult, Band, CriterionScore, ValidatedInput


def _band_for(score: float) -> Band:
    if score >= 0.70:
        return "strong"
    if score >= 0.40:
        return "moderate"
    return "weak"


def _unit_score(value: float, *, higher_is_better: bool) -> float:
    """Map 0-100 input to 0-1 unit score."""
    clamped = min(100.0, max(0.0, value))
    unit = clamped / 100.0
    return unit if higher_is_better else 1.0 - unit


def analyze(
    validated: ValidatedInput,
    *,
    criteria: tuple[CriterionDef, ...] | None = None,
) -> AnalysisResult:
    defs = criteria if criteria is not None else active_criteria()
    if not defs:
        return AnalysisResult(total_score=0.0, band="weak", criteria=[])

    weight_sum = sum(item.weight for item in defs)
    if weight_sum <= 0:
        msg = "Criterion weights must sum to a positive value"
        raise ValueError(msg)

    scores: list[CriterionScore] = []
    total = 0.0
    for item in defs:
        raw_param = validated.parameters.get(item.param_key, 0.0)
        if isinstance(raw_param, bool) or not isinstance(raw_param, (int, float)):
            raw_value = 0.0
        else:
            raw_value = float(raw_param)
        raw = _unit_score(raw_value, higher_is_better=item.higher_is_better)
        norm_weight = item.weight / weight_sum
        weighted = raw * norm_weight
        total += weighted
        direction = "higher better" if item.higher_is_better else "lower better"
        scores.append(
            CriterionScore(
                criterion_id=item.id,
                label=item.label,
                weight=norm_weight,
                raw_score=raw,
                weighted_score=weighted,
                rationale=f"{item.param_key}={raw_value:g} ({direction})",
            ),
        )

    # Clamp floating residue into [0, 1].
    total = min(1.0, max(0.0, total))
    return AnalysisResult(total_score=total, band=_band_for(total), criteria=scores)
