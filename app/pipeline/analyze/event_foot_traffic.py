"""Temporary foot-traffic / event-venue uplift near a precise store address.

When the operator opts in, we scan Kakao Local for venues that commonly host
large temporary crowds (stadiums, halls, expo centres, …) within a short
radius, score multi-factor uplift, and expose a demand multiplier for ROP.

Live event calendars are not available via Kakao; venue proximity is used as a
deterministic proxy for "likely temporary foot-traffic risk".
"""

from __future__ import annotations

import math
import re
from typing import Literal

from app.pipeline.types import EventVenueSignal

# User contract: only venues inside this radius count.
EVENT_SCAN_RADIUS_M = 200

# Soft-sat half point for raw venue score → uplift in [0, 1].
_EVENT_HALF_SAT = 1.6
# Distance decay for temporary-crowd influence (tighter than structural FTI).
_EVENT_DECAY_M = 100.0
# Cap on demand uplift fraction (effective_D = D * (1 + frac)).
EVENT_DEMAND_MAX_FRAC = 0.35
# How much event uplift can blend into structural FTI for Z context.
EVENT_FTI_BLEND = 0.20

EventKind = Literal[
    "stadium",
    "concert",
    "exhibition",
    "culture",
    "cinema",
    "other_event",
]

# Multi-angle weights: capacity proxy by venue class.
EVENT_KIND_WEIGHT: dict[EventKind, float] = {
    "stadium": 1.0,
    "concert": 0.85,
    "exhibition": 0.75,
    "culture": 0.45,
    "cinema": 0.25,
    "other_event": 0.35,
}

# Kakao keyword queries (parallel, capped) — venue proxies for temporary crowds.
EVENT_KEYWORD_QUERIES: tuple[str, ...] = (
    "경기장",
    "공연장",
    "전시장",
    "컨벤션",
)

_KIND_PATTERNS: list[tuple[EventKind, re.Pattern[str]]] = [
    (
        "stadium",
        re.compile(
            r"경기장|스타디움|야구장|축구장|월드컵|종합운동|스포츠콤플렉스|arena|stadium",
            re.I,
        ),
    ),
    (
        "concert",
        re.compile(
            r"공연장|콘서트|아레나|뮤직홀|오페라|연극|소극장|대극장|live\s*hall",
            re.I,
        ),
    ),
    (
        "exhibition",
        re.compile(
            r"전시장|전시회|컨벤션|박람|무역센터|코엑스|킨텍스|exco|setec|bexco",
            re.I,
        ),
    ),
    (
        "culture",
        re.compile(r"문화회관|예술의전당|시민회관|아트센터|미술관|박물관", re.I),
    ),
    ("cinema", re.compile(r"영화관|시네마|cgv|롯데시네마|메가박스", re.I)),
]

# Map keyword query → default kind when name does not reclassify.
_QUERY_DEFAULT_KIND: dict[str, EventKind] = {
    "경기장": "stadium",
    "공연장": "concert",
    "전시장": "exhibition",
    "컨벤션": "exhibition",
}


def classify_event_venue(name: str, *, query_hint: str = "") -> EventKind | None:
    """Return venue kind from place name, or None if not an event-crowd venue."""
    text = name.strip()
    if not text:
        return None
    for kind, pattern in _KIND_PATTERNS:
        if pattern.search(text):
            return kind
    hint = query_hint.strip()
    if hint in _QUERY_DEFAULT_KIND:
        # Keyword hit without strong name pattern still counts as weak proxy.
        return _QUERY_DEFAULT_KIND[hint]
    return None


def score_event_venues(
    venues: list[EventVenueSignal],
    *,
    radius_m: int = EVENT_SCAN_RADIUS_M,
) -> tuple[float, float, list[EventVenueSignal]]:
    """Multi-factor temporary-crowd uplift.

    Returns:
      (uplift in [0,1], demand_multiplier >= 1, scored venues sorted by weight)
    """
    if not venues:
        return 0.0, 1.0, []

    scored: list[EventVenueSignal] = []
    raw = 0.0
    by_kind_rank: dict[str, int] = {}

    ordered = sorted(venues, key=lambda v: v.distance_m)
    for venue in ordered:
        if venue.distance_m > radius_m * 1.05:
            continue
        kind_key: EventKind = (
            venue.kind if venue.kind in EVENT_KIND_WEIGHT else "other_event"  # type: ignore[assignment]
        )
        if kind_key not in EVENT_KIND_WEIGHT:
            kind_key = "other_event"
        kind_w = EVENT_KIND_WEIGHT[kind_key]
        kind = kind_key
        dist_f = math.exp(-max(0.0, venue.distance_m) / _EVENT_DECAY_M)
        rank = by_kind_rank.get(kind, 0)
        by_kind_rank[kind] = rank + 1
        rank_f = 0.5**rank
        contribution = kind_w * dist_f * rank_f
        raw += contribution
        scored.append(
            EventVenueSignal(
                name=venue.name,
                kind=kind,
                distance_m=venue.distance_m,
                weight=round(contribution, 4),
            ),
        )

    if raw <= 0.0:
        return 0.0, 1.0, []

    uplift = raw / (raw + _EVENT_HALF_SAT)
    uplift = round(min(1.0, max(0.0, uplift)), 4)
    multiplier = round(1.0 + EVENT_DEMAND_MAX_FRAC * uplift, 4)
    scored_sorted = sorted(scored, key=lambda v: v.weight, reverse=True)
    return uplift, multiplier, scored_sorted


def blend_fti_with_event(foot_traffic_index: float, event_uplift: float) -> float:
    """Structural FTI + temporary event blend, capped at 1.0."""
    fti = min(1.0, max(0.0, foot_traffic_index))
    uplift = min(1.0, max(0.0, event_uplift))
    return round(min(1.0, fti + EVENT_FTI_BLEND * uplift), 4)
