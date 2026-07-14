"""Deterministic role (frame) detection from table headers — adapter front (T56/T57).

Scores how well a header set matches each canonical frame using alias-aware
column resolution. No LLM. Used by detect-roles API and tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.column_aliases import build_column_rename_map
from app.domain.columns import ALL_SOURCE_COLUMNS, SourceFile

# Distinctive columns that strongly signal a frame when present.
_SIGNATURE_COLUMNS: dict[SourceFile, frozenset[str]] = {
    SourceFile.PROMOTION_PLAN: frozenset(
        {"promotion_id", "promo_price", "start_date", "end_date", "benefit_type"}
    ),
    SourceFile.PRODUCT_MASTER: frozenset({"normal_price", "cost", "product_name"}),
    SourceFile.INVENTORY: frozenset({"stock_qty", "inbound_date", "expected_demand"}),
}


@dataclass(frozen=True, slots=True)
class RoleScore:
    role: SourceFile
    score: float
    matched_columns: tuple[str, ...]
    missing_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoleSuggestion:
    suggested_role: SourceFile | None
    confidence: float
    scores: tuple[RoleScore, ...]


def _matched_canonicals(headers: list[str], expected: tuple[str, ...]) -> tuple[str, ...]:
    rename_map, missing = build_column_rename_map(headers, expected)
    claimed = set(expected) - set(missing)
    # rename targets + exact already-canonical
    for _original, canonical in rename_map.items():
        claimed.add(canonical)
    # headers that already equal canonical names
    stripped = {str(h).strip() for h in headers}
    for column in expected:
        if column in stripped:
            claimed.add(column)
    ordered = tuple(column for column in expected if column in claimed)
    return ordered


def score_headers_for_role(headers: list[str], role: SourceFile) -> RoleScore:
    expected = ALL_SOURCE_COLUMNS[role]
    matched = _matched_canonicals(headers, expected)
    missing = tuple(column for column in expected if column not in matched)
    if not expected:
        return RoleScore(role=role, score=0.0, matched_columns=(), missing_columns=())

    coverage = len(matched) / len(expected)
    signature = _SIGNATURE_COLUMNS.get(role, frozenset())
    sig_hits = len(signature.intersection(matched))
    sig_bonus = (sig_hits / len(signature)) * 0.35 if signature else 0.0
    # Prefer frames that match more absolute columns when coverage ties.
    density = min(len(matched) / 6.0, 0.15)
    score = min(1.0, coverage * 0.7 + sig_bonus + density)
    return RoleScore(
        role=role,
        score=round(score, 4),
        matched_columns=matched,
        missing_columns=missing,
    )


def suggest_role(headers: list[str], *, min_score: float = 0.28) -> RoleSuggestion:
    """Return best frame for headers, or None if all scores are weak."""
    scores = tuple(
        sorted(
            (score_headers_for_role(headers, role) for role in SourceFile),
            key=lambda item: item.score,
            reverse=True,
        )
    )
    if not scores:
        return RoleSuggestion(suggested_role=None, confidence=0.0, scores=())
    best = scores[0]
    second = scores[1].score if len(scores) > 1 else 0.0
    if best.score < min_score:
        return RoleSuggestion(suggested_role=None, confidence=best.score, scores=scores)
    # Require a small margin so ambiguous tables stay unassigned.
    if best.score - second < 0.05 and best.score < 0.55:
        return RoleSuggestion(suggested_role=None, confidence=best.score, scores=scores)
    return RoleSuggestion(
        suggested_role=best.role,
        confidence=best.score,
        scores=scores,
    )


def assign_roles_greedy(
    artifacts: list[tuple[str, list[str]]],
) -> dict[str, SourceFile | None]:
    """Greedy unique assignment: highest (artifact, role) scores without role reuse.

    ``artifacts`` is a list of ``(artifact_id, headers)``.
    Returns map artifact_id → role or None.
    """
    candidates: list[tuple[float, str, SourceFile]] = []
    for artifact_id, headers in artifacts:
        suggestion = suggest_role(headers)
        for role_score in suggestion.scores:
            if role_score.score < 0.2:
                continue
            candidates.append((role_score.score, artifact_id, role_score.role))
    candidates.sort(key=lambda item: item[0], reverse=True)

    assigned_roles: set[SourceFile] = set()
    assignment: dict[str, SourceFile | None] = {artifact_id: None for artifact_id, _ in artifacts}
    for _score, artifact_id, role in candidates:
        if assignment[artifact_id] is not None:
            continue
        if role in assigned_roles:
            continue
        assignment[artifact_id] = role
        assigned_roles.add(role)
        if len(assigned_roles) == len(SourceFile):
            break
    return assignment
