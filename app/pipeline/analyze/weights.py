"""Pre-configured evaluation weights (skeleton placeholders).

Production weights must be replaced with researched values (redesign board R1/R3).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CriterionDef:
    id: str
    label: str
    weight: float
    """Relative weight; weights are normalized at analyze time."""
    higher_is_better: bool
    """If False, raw 0-100 values are inverted before scoring."""
    param_key: str


# Placeholder criteria — not production research.
SKELETON_CRITERIA: tuple[CriterionDef, ...] = (
    CriterionDef(
        id="quality",
        label="Quality",
        weight=0.45,
        higher_is_better=True,
        param_key="quality",
    ),
    CriterionDef(
        id="cost_efficiency",
        label="Cost efficiency",
        weight=0.30,
        higher_is_better=False,
        param_key="cost",
    ),
    CriterionDef(
        id="risk_control",
        label="Risk control",
        weight=0.25,
        higher_is_better=False,
        param_key="risk",
    ),
)


def active_criteria() -> tuple[CriterionDef, ...]:
    return SKELETON_CRITERIA
