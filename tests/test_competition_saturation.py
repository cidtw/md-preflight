"""Unit tests for competition / market-saturation demand dispersion."""

from __future__ import annotations

from app.pipeline.analyze.competition_saturation import (
    COMPETITION_DEMAND_MAX_FRAC,
    SELF_EXCLUDE_M,
    classify_competitor,
    competition_demand_factor,
    competitor_queries,
    profile_for_store_type,
    score_competitors,
)
from app.pipeline.analyze.engine import analyze
from app.pipeline.input.template import validate_parameters
from app.pipeline.types import CompetitionCompetitor, GeoEnrichment, ParameterValue

BASE: dict[str, ParameterValue] = {
    "product_name": "생수 500ml",
    "store_type": "convenience",
    "store_size": "cv_s",
    "avg_ticket": "t_le_8k",
    "location_dong": "서울시 마포구 합정동",
    "trade_area": "office",
    "accessibility": "main_road",
    "daily_demand": 20,
    "standard_lead_time_days": 2,
    "standard_rop": 40,
}


def test_profiles_follow_industry_radii() -> None:
    assert profile_for_store_type("convenience").primary_radius_m == 300
    assert profile_for_store_type("supermarket").search_radius_m == 1000
    assert profile_for_store_type("ssm").primary_radius_m == 1000
    assert profile_for_store_type("hypermarket").primary_radius_m == 5000


def test_competitor_queries_cover_tiers() -> None:
    cvs = competitor_queries("convenience")
    assert any(q.tier == "direct" for q in cvs)
    assert any(q.default_kind == "convenience" for q in cvs)
    sm = competitor_queries("supermarket")
    assert any(q.tier == "threat" and q.default_kind == "ssm" for q in sm)


def test_classify_competitor_kinds() -> None:
    assert classify_competitor("GS25 합정점", default_kind="convenience") == "convenience"
    assert classify_competitor("이마트 에브리데이 연남", default_kind="ssm") == "ssm"
    assert classify_competitor("코스트코 양재", default_kind="warehouse") == "warehouse"
    assert (
        classify_competitor("이름없음", default_kind="food_mart", query_hint="식자재")
        == "food_mart"
    )


def test_classify_unmanned_discount_not_hypermarket() -> None:
    """Bare 할인점 + 무인 must not land as hypermarket (inflates tier weight)."""
    assert (
        classify_competitor("무인 아이스크림 할인점", default_kind="hypermarket")
        == "unmanned_specialty"
    )
    assert (
        classify_competitor("무인 세계과자 전문점", default_kind="convenience")
        == "unmanned_specialty"
    )
    # Known hyper anchors still classify as hyper even if default differs.
    assert classify_competitor("이마트 마포점", default_kind="other_retail") == "hypermarket"
    assert classify_competitor("롯데마트 잠실", default_kind="hypermarket") == "hypermarket"


def test_score_competitors_near_direct_lowers_demand() -> None:
    comps = [
        CompetitionCompetitor(
            name="CU 옆집",
            kind="convenience",
            tier="direct",
            distance_m=80.0,
        ),
        CompetitionCompetitor(
            name="GS25 골목",
            kind="convenience",
            tier="direct",
            distance_m=120.0,
        ),
    ]
    intensity, factor, scored = score_competitors(
        comps,
        decay_m=120.0,
        max_radius_m=300,
    )
    assert intensity > 0
    assert factor < 1.0
    assert factor >= 1.0 - COMPETITION_DEMAND_MAX_FRAC - 1e-9
    assert scored
    assert scored[0].weight > 0


def test_score_excludes_self_and_far() -> None:
    comps = [
        CompetitionCompetitor(
            name="자점 추정",
            kind="convenience",
            tier="direct",
            distance_m=SELF_EXCLUDE_M - 1,
        ),
        CompetitionCompetitor(
            name="먼 점포",
            kind="convenience",
            tier="direct",
            distance_m=900.0,
        ),
    ]
    intensity, factor, scored = score_competitors(
        comps,
        decay_m=120.0,
        max_radius_m=300,
    )
    assert intensity == 0.0
    assert factor == 1.0
    assert scored == []


def test_competition_demand_factor_bounds() -> None:
    assert competition_demand_factor(0.0) == 1.0
    assert competition_demand_factor(1.0) == round(1.0 - COMPETITION_DEMAND_MAX_FRAC, 4)


def test_consider_competition_requires_precise() -> None:
    validated = validate_parameters(
        {
            **BASE,
            "use_precise_location": False,
            "consider_competition_saturation": True,
        },
    )
    assert validated.parameters.get("consider_competition_saturation") is False
    assert any("경쟁" in g for g in validated.guidance)


def test_engine_competition_lowers_effective_demand_and_rop() -> None:
    validated = validate_parameters(
        {
            **BASE,
            "use_precise_location": True,
            "store_address": "서울 마포구 양화로 45",
            "consider_competition_saturation": True,
        },
    )
    base_geo = GeoEnrichment(
        enabled=True,
        used_fallback=False,
        provider="kakao",
        foot_traffic_index=0.2,
        competition_scan_enabled=True,
        competition_radius_m=500,
        competition_primary_radius_m=300,
        competition_store_type="convenience",
        competition_intensity=0.5,
        competition_demand_factor=0.8,
        competitors=[
            CompetitionCompetitor(
                name="CU 테스트",
                kind="convenience",
                tier="direct",
                distance_m=90.0,
                weight=0.5,
            ),
        ],
    )
    neutral = GeoEnrichment(
        enabled=True,
        used_fallback=False,
        provider="kakao",
        foot_traffic_index=0.2,
        competition_scan_enabled=False,
        competition_demand_factor=1.0,
    )
    with_comp = analyze(validated, geo_override=base_geo)
    without = analyze(validated, geo_override=neutral)
    assert with_comp.competition_demand_factor == 0.8
    assert with_comp.competition_demand_cut_frac == 0.2
    assert with_comp.effective_daily_demand < without.effective_daily_demand
    assert with_comp.recommended_rop < without.recommended_rop
    # Standard baseline stays on unadjusted D.
    assert with_comp.standard_rop == without.standard_rop


def test_engine_event_and_competition_compose() -> None:
    validated = validate_parameters(
        {
            **BASE,
            "use_precise_location": True,
            "store_address": "서울 마포구 양화로 45",
            "consider_temp_foot_traffic": True,
            "consider_competition_saturation": True,
        },
    )
    geo = GeoEnrichment(
        enabled=True,
        used_fallback=False,
        provider="kakao",
        foot_traffic_index=0.3,
        event_scan_enabled=True,
        event_demand_multiplier=1.2,
        event_foot_traffic_uplift=0.5,
        competition_scan_enabled=True,
        competition_intensity=0.5,
        competition_demand_factor=0.8,
    )
    calc = analyze(validated, geo_override=geo)
    # D * 1.2 * 0.8 = D * 0.96 (inside 0.5x-2.0x global band)
    assert abs(calc.effective_daily_demand - 20 * 1.2 * 0.8) < 1e-6
    assert calc.effective_demand_clamped is False
    assert abs(calc.effective_daily_demand_uncapped - calc.effective_daily_demand) < 1e-6

    from app.pipeline.output.recommendation import render

    report = render(validated, calc)
    geo_plain = next(b for b in report.evidence if b.id == "geo_poi")
    plain = " ".join(geo_plain.points)
    assert "집적" in plain
    geo_tech = next(b for b in report.evidence_technical if b.id == "geo_poi")
    tech = " ".join(geo_tech.points)
    assert "agglomeration" in tech.lower() or "leak" in tech.lower()
    assert any("스냅샷" in g for g in report.guidance)
