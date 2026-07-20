"""Competition / market-saturation demand dispersion near a precise store.

When the operator opts in (precise address only), we scan Kakao Local for
competing retail within an industry-standard primary trade-area radius, score
distance x adjacency (tier) intensity, and expose a demand factor <= 1 that
weakens ROP inputs under market saturation.

Weights follow domestic retail practice + KFTC-style market radii (CVS /
supermart / SSM / hypermarket). Live chain-level market-share data is not used;
proximity of competitor venues is a deterministic proxy.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Final, Literal

from app.pipeline.types import CompetitionCompetitor

# Soft-sat for raw competition score → intensity in [0, 1].
_COMP_HALF_SAT = 1.8
# Max fraction of demand removed at full saturation intensity.
COMPETITION_DEMAND_MAX_FRAC: Final[float] = 0.40
# Ignore hits closer than this (likely the subject store itself).
SELF_EXCLUDE_M: Final[float] = 30.0
# Within-tier rank decay (2nd nearest same tier half weight, …).
_RANK_DECAY = 0.5

CompetitorTier = Literal["direct", "threat", "indirect"]
CompetitorKind = Literal[
    "convenience",
    "small_super",
    "ssm",
    "food_mart",
    "hypermarket",
    "warehouse",
    "traditional_market",
    "unmanned_specialty",
    "other_retail",
]

# Tier adjacency weights: direct competition > same-life-zone threat > indirect.
TIER_WEIGHT: Final[dict[CompetitorTier, float]] = {
    "direct": 1.0,
    "threat": 0.85,
    "indirect": 0.40,
}

KIND_LABEL_KO: Final[dict[str, str]] = {
    "convenience": "편의점",
    "small_super": "개인·중소 슈퍼",
    "ssm": "기업형 슈퍼(SSM)",
    "food_mart": "식자재 마트",
    "hypermarket": "대형마트·할인점",
    "warehouse": "창고형 할인점",
    "traditional_market": "전통시장",
    "unmanned_specialty": "무인·전문 할인점",
    "other_retail": "기타 유통",
}

TIER_LABEL_KO: Final[dict[str, str]] = {
    "direct": "직접 경쟁",
    "threat": "실질 위협",
    "indirect": "간접 경쟁",
}


@dataclass(frozen=True, slots=True)
class TradeAreaProfile:
    """Primary trade-area + search envelope for one store type."""

    store_type: str
    primary_radius_m: int
    search_radius_m: int
    decay_m: float
    notes: str


# RAG summary: CVS 100-300m, super 300-500m, SSM 500m-1km, hyper 3-5km.
TRADE_AREA_BY_TYPE: Final[dict[str, TradeAreaProfile]] = {
    "convenience": TradeAreaProfile(
        store_type="convenience",
        primary_radius_m=300,
        search_radius_m=500,
        decay_m=120.0,
        notes="편의점 1차 상권 100-300m(도보 초근접) · 간접 경쟁(SSM)은 500m까지",
    ),
    "supermarket": TradeAreaProfile(
        store_type="supermarket",
        primary_radius_m=500,
        search_radius_m=1000,
        decay_m=220.0,
        notes="일반 슈퍼 1차 상권 300-500m · SSM 위협은 1km",
    ),
    "ssm": TradeAreaProfile(
        store_type="ssm",
        primary_radius_m=1000,
        search_radius_m=3000,
        decay_m=450.0,
        notes="SSM 1차 상권 ~1km(공정위 기준 시장) · 상위 대형마트는 3km",
    ),
    "hypermarket": TradeAreaProfile(
        store_type="hypermarket",
        primary_radius_m=5000,
        search_radius_m=5000,
        decay_m=1800.0,
        notes="대형마트 1차 상권 3-5km(차량) · 식자재·SSM 침투 반영",
    ),
}


@dataclass(frozen=True, slots=True)
class CompetitorQuery:
    """One Kakao search task for competitors."""

    mode: Literal["category", "keyword"]
    code_or_query: str
    default_kind: CompetitorKind
    tier: CompetitorTier
    radius_m: int


def profile_for_store_type(store_type: str) -> TradeAreaProfile:
    return TRADE_AREA_BY_TYPE.get(store_type, TRADE_AREA_BY_TYPE["convenience"])


def competitor_queries(store_type: str) -> list[CompetitorQuery]:
    """Industry-matrix search plan (direct / threat / indirect) per channel."""
    p = profile_for_store_type(store_type)
    r0, r1 = p.primary_radius_m, p.search_radius_m

    if store_type == "convenience":
        return [
            CompetitorQuery("category", "CS2", "convenience", "direct", r0),
            CompetitorQuery("keyword", "슈퍼마켓", "small_super", "direct", r0),
            CompetitorQuery("keyword", "기업형 슈퍼", "ssm", "indirect", r1),
            CompetitorQuery("keyword", "이마트에브리데이", "ssm", "indirect", r1),
            CompetitorQuery("keyword", "롯데슈퍼", "ssm", "indirect", r1),
            CompetitorQuery("keyword", "홈플러스 익스프레스", "ssm", "indirect", r1),
            CompetitorQuery("keyword", "무인 아이스크림", "unmanned_specialty", "indirect", r0),
            CompetitorQuery("keyword", "세계과자", "unmanned_specialty", "indirect", r0),
        ]
    if store_type == "supermarket":
        return [
            CompetitorQuery("keyword", "슈퍼마켓", "small_super", "direct", r0),
            CompetitorQuery("keyword", "식자재마트", "food_mart", "direct", r0),
            CompetitorQuery("keyword", "이마트에브리데이", "ssm", "threat", r1),
            CompetitorQuery("keyword", "롯데슈퍼", "ssm", "threat", r1),
            CompetitorQuery("keyword", "홈플러스 익스프레스", "ssm", "threat", r1),
            CompetitorQuery("keyword", "GS더프레시", "ssm", "threat", r1),
            CompetitorQuery("category", "CS2", "convenience", "indirect", min(400, r0)),
            CompetitorQuery("keyword", "전통시장", "traditional_market", "indirect", r0),
        ]
    if store_type == "ssm":
        return [
            CompetitorQuery("keyword", "이마트에브리데이", "ssm", "direct", r0),
            CompetitorQuery("keyword", "롯데슈퍼", "ssm", "direct", r0),
            CompetitorQuery("keyword", "홈플러스 익스프레스", "ssm", "direct", r0),
            CompetitorQuery("keyword", "GS더프레시", "ssm", "direct", r0),
            CompetitorQuery("keyword", "식자재마트", "food_mart", "direct", r0),
            CompetitorQuery("keyword", "전통시장", "traditional_market", "direct", r0),
            CompetitorQuery("keyword", "슈퍼마켓", "small_super", "indirect", min(800, r0)),
            CompetitorQuery("category", "MT1", "hypermarket", "threat", r1),
            CompetitorQuery("keyword", "이마트", "hypermarket", "threat", r1),
            CompetitorQuery("keyword", "홈플러스", "hypermarket", "threat", r1),
        ]
    # hypermarket
    return [
        CompetitorQuery("category", "MT1", "hypermarket", "direct", r0),
        CompetitorQuery("keyword", "이마트", "hypermarket", "direct", r0),
        CompetitorQuery("keyword", "홈플러스", "hypermarket", "direct", r0),
        CompetitorQuery("keyword", "롯데마트", "hypermarket", "direct", r0),
        CompetitorQuery("keyword", "코스트코", "warehouse", "direct", r0),
        CompetitorQuery("keyword", "트레이더스", "warehouse", "direct", r0),
        CompetitorQuery("keyword", "식자재마트", "food_mart", "threat", r0),
        CompetitorQuery("keyword", "이마트에브리데이", "ssm", "indirect", min(2000, r0)),
        CompetitorQuery("keyword", "롯데슈퍼", "ssm", "indirect", min(2000, r0)),
        CompetitorQuery("keyword", "홈플러스 익스프레스", "ssm", "indirect", min(2000, r0)),
    ]


_KIND_PATTERNS: list[tuple[CompetitorKind, re.Pattern[str]]] = [
    (
        "warehouse",
        re.compile(r"코스트코|트레이더스|이마트\s*트레이더스|costco|warehouse", re.I),
    ),
    (
        "ssm",
        re.compile(
            (
                r"에브리데이|롯데슈퍼|홈플러스\s*익스프레스|GS\s*더\s*프레시|"
                + r"기업형\s*슈퍼|SSM|fresh"
            ),
            re.I,
        ),
    ),
    # Unmanned specialty before hyper: bare "할인점" alone is not a hypermarket.
    (
        "unmanned_specialty",
        re.compile(r"무인|아이스크림|세계과자", re.I),
    ),
    (
        "hypermarket",
        # Require chain/size anchors — bare "할인점" mis-tags unmanned specialty.
        re.compile(r"이마트|홈플러스|롯데마트|대형마트|하이퍼", re.I),
    ),
    (
        "food_mart",
        re.compile(r"식자재|도매마트|농수산\s*마트|식품\s*마트", re.I),
    ),
    (
        "traditional_market",
        re.compile(r"시장|재래시장|전통시장|골목시장", re.I),
    ),
    (
        "convenience",
        re.compile(
            r"편의점|CU|GS25|세븐일레븐|이마트24|이마트\s*24|7-?ELEVEN|미니스톱",
            re.I,
        ),
    ),
    (
        "small_super",
        re.compile(r"슈퍼|수퍼|마트", re.I),
    ),
]


def classify_competitor(
    name: str,
    *,
    default_kind: CompetitorKind,
    query_hint: str = "",
) -> CompetitorKind:
    """Refine competitor kind from place name; fall back to query default."""
    text = name.strip()
    if not text:
        return default_kind
    # Explicit unmanned priority (e.g. "무인 아이스크림 할인점").
    if re.search(r"무인", text, re.I):
        return "unmanned_specialty"
    for kind, pattern in _KIND_PATTERNS:
        if pattern.search(text):
            # Avoid classifying pure "마트" hyper hits as small_super when query is MT1.
            if kind == "small_super" and default_kind in {
                "hypermarket",
                "warehouse",
                "ssm",
                "food_mart",
            }:
                continue
            return kind
    if query_hint:
        for kind, pattern in _KIND_PATTERNS:
            if pattern.search(query_hint):
                return kind
    return default_kind


def score_competitors(
    competitors: list[CompetitionCompetitor],
    *,
    decay_m: float,
    max_radius_m: int,
) -> tuple[float, float, list[CompetitionCompetitor]]:
    """Return (intensity ∈[0,1], demand_factor ∈[1-max_frac,1], scored list)."""
    if decay_m <= 0:
        decay_m = 120.0
    eligible: list[CompetitionCompetitor] = []
    for c in competitors:
        if c.distance_m < SELF_EXCLUDE_M:
            continue
        if c.distance_m > max_radius_m * 1.05:
            continue
        eligible.append(c)

    # Dedupe by name, keep nearest.
    by_name: dict[str, CompetitionCompetitor] = {}
    for c in sorted(eligible, key=lambda x: x.distance_m):
        if c.name not in by_name:
            by_name[c.name] = c
    unique = list(by_name.values())

    # Rank within tier for decay.
    by_tier: dict[CompetitorTier, list[CompetitionCompetitor]] = {}
    for c in unique:
        tier = c.tier if c.tier in TIER_WEIGHT else "indirect"
        by_tier.setdefault(tier, []).append(c)  # type: ignore[arg-type]

    raw = 0.0
    scored: list[CompetitionCompetitor] = []
    for tier, group in by_tier.items():
        tier_w = TIER_WEIGHT.get(tier, TIER_WEIGHT["indirect"])  # type: ignore[arg-type]
        ordered = sorted(group, key=lambda x: x.distance_m)
        for rank, c in enumerate(ordered):
            dist_f = math.exp(-max(0.0, c.distance_m) / decay_m)
            rank_f = _RANK_DECAY**rank
            w = round(tier_w * dist_f * rank_f, 4)
            scored.append(
                CompetitionCompetitor(
                    name=c.name,
                    kind=c.kind,
                    tier=c.tier,
                    distance_m=c.distance_m,
                    weight=w,
                ),
            )
            raw += w

    scored.sort(key=lambda x: (-x.weight, x.distance_m))
    if raw <= 0.0:
        return 0.0, 1.0, []
    intensity = raw / (raw + _COMP_HALF_SAT)
    intensity = round(min(1.0, max(0.0, intensity)), 4)
    demand_factor = round(1.0 - COMPETITION_DEMAND_MAX_FRAC * intensity, 4)
    demand_factor = min(1.0, max(1.0 - COMPETITION_DEMAND_MAX_FRAC, demand_factor))
    return intensity, demand_factor, scored


def competition_demand_factor(intensity: float) -> float:
    i = min(1.0, max(0.0, intensity))
    return round(1.0 - COMPETITION_DEMAND_MAX_FRAC * i, 4)
