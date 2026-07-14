"""Stage 3 — one-line recommendation rendering."""

from __future__ import annotations

from app.pipeline.types import AnalysisResult, RecommendationResult, ValidatedInput

_BAND_LINES: dict[str, str] = {
    "strong": "Recommend proceed: overall fit is strong under the configured weights.",
    "moderate": "Recommend conditional proceed: overall fit is moderate; review weak criteria.",
    "weak": "Recommend hold: overall fit is weak under the configured weights.",
}


def render(
    validated: ValidatedInput,
    analysis: AnalysisResult,
) -> RecommendationResult:
    line = _BAND_LINES[analysis.band]
    # Include score in the one-liner for auditability without changing band logic.
    recommendation = f"{line} (score={analysis.total_score:.2f})"
    return RecommendationResult(
        recommendation=recommendation,
        score=analysis.total_score,
        band=analysis.band,
        template_id=validated.template_id,
        template_version=validated.template_version,
        details=analysis,
    )
