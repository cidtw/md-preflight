"""Unit tests for temporary event-crowd uplift scoring and engine wiring."""

from __future__ import annotations

import pytest

from app.pipeline.analyze.engine import analyze
from app.pipeline.analyze.event_foot_traffic import (
    EVENT_DEMAND_MAX_FRAC,
    EVENT_SCAN_RADIUS_M,
    blend_fti_with_event,
    classify_event_venue,
    score_event_venues,
)
from app.pipeline.input.template import validate_parameters
from app.pipeline.types import EventVenueSignal, GeoEnrichment, ParameterValue

BASE: dict[str, ParameterValue] = {
    "product_name": "냉장 간편식",
    "store_type": "convenience",
    "store_size": "cv_s",
    "avg_ticket": "t_le_8k",
    "location_dong": "서울시 마포구 서교동",
    "trade_area": "office",
    "accessibility": "main_road",
    "daily_demand": 10,
    "standard_lead_time_days": 2,
    "standard_rop": 20,
}


def test_classify_event_venue_kinds() -> None:
    assert classify_event_venue("서울월드컵경기장") == "stadium"
    assert classify_event_venue("블루스퀘어 공연장") == "concert"
    assert classify_event_venue("코엑스 전시장") == "exhibition"
    assert classify_event_venue("CGV 여의도") == "cinema"
    assert classify_event_venue("일반 카페") is None
    assert classify_event_venue("무명", query_hint="경기장") == "stadium"


def test_score_event_venues_near_stadium_raises_demand() -> None:
    venues = [
        EventVenueSignal(name="테스트 경기장", kind="stadium", distance_m=80.0),
        EventVenueSignal(name="작은 영화관", kind="cinema", distance_m=50.0),
    ]
    uplift, mult, scored = score_event_venues(venues, radius_m=EVENT_SCAN_RADIUS_M)
    assert uplift > 0
    assert mult > 1.0
    assert mult <= 1.0 + EVENT_DEMAND_MAX_FRAC + 1e-9
    assert scored
    assert scored[0].weight > 0


def test_score_event_venues_outside_radius_ignored() -> None:
    venues = [
        EventVenueSignal(name="먼 경기장", kind="stadium", distance_m=500.0),
    ]
    uplift, mult, scored = score_event_venues(venues, radius_m=200)
    assert uplift == 0.0
    assert mult == 1.0
    assert scored == []


def test_blend_fti_with_event() -> None:
    assert blend_fti_with_event(0.4, 0.0) == 0.4
    blended = blend_fti_with_event(0.4, 1.0)
    assert blended > 0.4
    assert blended <= 1.0


def test_consider_temp_requires_precise_address_stripped() -> None:
    validated = validate_parameters(
        {
            **BASE,
            "use_precise_location": False,
            "consider_temp_foot_traffic": True,
        },
    )
    assert validated.parameters.get("consider_temp_foot_traffic") is False
    assert any("일시 유동" in g or "일시" in g for g in validated.guidance)


def test_engine_applies_event_demand_multiplier() -> None:
    validated = validate_parameters(
        {
            **BASE,
            "use_precise_location": True,
            "store_address": "서울시 마포구 양화로 45",
            "consider_temp_foot_traffic": True,
        },
    )
    geo = GeoEnrichment(
        enabled=True,
        used_fallback=False,
        provider="test",
        foot_traffic_index=0.2,
        address_queried="서울시 마포구 양화로 45",
        event_scan_enabled=True,
        event_radius_m=200,
        event_venues=[
            EventVenueSignal(
                name="테스트 공연장",
                kind="concert",
                distance_m=60.0,
                weight=0.5,
            ),
        ],
        event_foot_traffic_uplift=0.5,
        event_demand_multiplier=1.0 + EVENT_DEMAND_MAX_FRAC * 0.5,
    )
    calc = analyze(validated, geo_override=geo)
    assert calc.event_demand_uplift_frac == pytest.approx(EVENT_DEMAND_MAX_FRAC * 0.5)
    assert calc.effective_daily_demand == pytest.approx(
        calc.daily_demand * geo.event_demand_multiplier,
    )
    # ROP identity on effective demand.
    d_eff = calc.effective_daily_demand
    assert calc.recommended_rop == pytest.approx(
        d_eff * calc.standard_lead_time_days + calc.store_safety_stock,
        abs=0.05,
    )
    # Without event, ROP would be lower for same inputs (structural path only).
    geo_off = GeoEnrichment(
        enabled=True,
        used_fallback=False,
        provider="test",
        foot_traffic_index=0.2,
        address_queried="서울시 마포구 양화로 45",
        event_scan_enabled=False,
        event_demand_multiplier=1.0,
    )
    calc_off = analyze(validated, geo_override=geo_off)
    assert calc.recommended_rop >= calc_off.recommended_rop - 1e-6
