"""Unit tests for place ranking and competition simulation (no live Kakao)."""

from __future__ import annotations

from app.pipeline.analyze.competition_sim import SimulationRequest, run_simulation
from app.pipeline.analyze.decline_advice import (
    fallback_decline_advice,
    generate_decline_advice,
)
from app.pipeline.analyze.store_search import (
    PlaceSuggestion,
    _similarity,
    search_places,
)
from app.pipeline.region_catalog import list_sido, list_sigungu, region_prefix
from app.pipeline.types import CompetitionCompetitor, GeoEnrichment, ParameterValue


def test_region_catalog_seoul_mapo() -> None:
    assert "서울특별시" in list_sido()
    assert "마포구" in list_sigungu("서울특별시")
    assert region_prefix(sido="서울특별시", sigungu="마포구", dong="신수동") == (
        "서울특별시 마포구 신수동"
    )


def test_similarity_prefers_name_substring() -> None:
    q = "GS25 뉴서강"
    high = _similarity(q, "GS25 뉴서강대학사점", "서울 마포구 백범로 35")
    low = _similarity(q, "이마트 여의도점", "서울 영등포구 여의대로 108")
    assert high > low


def test_search_places_without_key_fallback() -> None:
    res = search_places(
        "GS25 뉴서강",
        api_key=None,
        sido="서울특별시",
        sigungu="마포구",
    )
    assert res.used_fallback is True
    assert res.results == []
    assert res.notes


def test_search_places_with_mock_fetch() -> None:
    def fetch(url: str, _headers: object) -> dict[str, object]:
        if "keyword" in url:
            return {
                "documents": [
                    {
                        "id": "1",
                        "place_name": "GS25 뉴서강대학사점",
                        "road_address_name": "서울 마포구 백범로 35",
                        "address_name": "서울 마포구 신수동 1",
                        "category_name": "가정,생활 > 편의점",
                        "phone": "",
                        "x": "126.93",
                        "y": "37.55",
                    },
                    {
                        "id": "2",
                        "place_name": "CU 서강대점",
                        "road_address_name": "서울 마포구 백범로 10",
                        "address_name": "서울 마포구 신수동 2",
                        "category_name": "가정,생활 > 편의점",
                        "x": "126.94",
                        "y": "37.55",
                    },
                ],
            }
        return {"documents": []}

    res = search_places(
        "GS25 뉴서강",
        api_key="test-key",
        sido="서울특별시",
        sigungu="마포구",
        store_type="convenience",
        fetch=fetch,
    )
    assert res.used_fallback is False
    assert res.results
    assert "GS25" in res.results[0].name
    assert res.results[0].road_address.startswith("서울")


def test_simulation_competitor_pressure_lowers_demand() -> None:
    params: dict[str, ParameterValue] = {
        "product_name": "생수",
        "store_type": "convenience",
        "store_size": "cv_s",
        "avg_ticket": "t_le_8k",
        "location_dong": "서울시 마포구 신수동",
        "trade_area": "campus",
        "accessibility": "main_road",
        "daily_demand": 40,
        "standard_lead_time_days": 2,
    }
    out = run_simulation(
        SimulationRequest(
            parameters=params,
            scenario="competitor_pressure",
            intensity=0.8,
        ),
    )
    assert out.shocked.daily_demand < out.baseline.daily_demand
    assert out.own_sales_index_delta_pct < 0
    assert out.competitor_response_note
    # Sales decline path must populate AI/fallback advice for the UI panel.
    assert out.sales_decline is True
    assert out.ai_advice
    assert "ROP" in out.ai_advice or "안전재고" in out.ai_advice
    assert out.ai_used is False
    assert out.ai_note


def test_competitor_pressure_is_demand_leak_only_not_double_comp() -> None:
    """Pressure multiplies D by up to -28%; competition_factor stays shared via geo."""
    params: dict[str, ParameterValue] = {
        "product_name": "생수",
        "store_type": "convenience",
        "store_size": "cv_s",
        "avg_ticket": "t_le_8k",
        "location_dong": "서울시 마포구 신수동",
        "trade_area": "campus",
        "accessibility": "main_road",
        "daily_demand": 50,
        "standard_lead_time_days": 2,
        "use_precise_location": True,
        "store_address": "서울 마포구 양화로 45",
        "consider_competition_saturation": True,
    }
    geo = GeoEnrichment(
        enabled=True,
        used_fallback=False,
        provider="kakao",
        foot_traffic_index=0.2,
        competition_scan_enabled=True,
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
    intensity = 1.0
    out = run_simulation(
        SimulationRequest(
            parameters=params,
            scenario="competitor_pressure",
            intensity=intensity,
        ),
        geo_override=geo,
    )
    # Same competition factor on both sides (no second saturation layer).
    assert out.baseline.competition_demand_factor == 0.8
    assert out.shocked.competition_demand_factor == 0.8
    # Pure demand leak: D' = D * (1 - 0.28 * i)
    assert out.shocked.daily_demand == 36.0  # 50 * 0.72
    # Effective demand also scales by the shared factor only once each.
    assert abs(out.baseline.effective_daily_demand - 50 * 0.8) < 1e-6
    assert abs(out.shocked.effective_daily_demand - 36.0 * 0.8) < 1e-6
    # Decline approx -28%, not -28% *and* an extra competition cut.
    assert abs(out.own_sales_index_delta_pct - (-28.0)) < 0.2


def test_decline_advice_fallback_without_api_key() -> None:
    text, used, note = generate_decline_advice(
        parameters={
            "product_name": "생수",
            "store_type": "convenience",
            "store_size": "cv_s",
            "avg_ticket": "t_le_8k",
            "location_dong": "서울시 마포구 신수동",
            "trade_area": "campus",
            "accessibility": "main_road",
            "daily_demand": 40,
            "standard_lead_time_days": 2,
        },
        scenario_label="경쟁 매장 공세(포화 심화)",
        intensity=0.8,
        delta_pct=-22.4,
        plain_summary="테스트 요약",
        baseline={
            "daily_demand": 40,
            "effective_daily_demand": 40,
            "recommended_rop": 100,
            "store_safety_stock": 20,
            "suggested_order_qty": 80,
            "standard_lead_time_days": 2,
            "competition_demand_factor": 1.0,
        },
        shocked={
            "daily_demand": 30,
            "effective_daily_demand": 30,
            "recommended_rop": 75,
            "store_safety_stock": 15,
            "suggested_order_qty": 60,
            "standard_lead_time_days": 2,
            "competition_demand_factor": 1.0,
        },
        api_key=None,
    )
    assert used is False
    assert note and "XAI_API_KEY" in note
    assert "로컬 폴백" in text
    assert "75.0" in text  # shocked ROP
    # Deterministic helper matches the same numbers.
    fb = fallback_decline_advice(
        delta_pct=-22.4,
        rop_now=100,
        rop_after=75,
        ss_now=20,
        ss_after=15,
        q_now=80,
        q_after=60,
    )
    assert "로컬 폴백" in fb


def test_simulation_own_service_up_raises_rop_or_demand() -> None:
    params: dict[str, ParameterValue] = {
        "product_name": "생수",
        "store_type": "convenience",
        "store_size": "cv_s",
        "avg_ticket": "t_le_8k",
        "location_dong": "서울시 마포구 신수동",
        "trade_area": "campus",
        "accessibility": "main_road",
        "daily_demand": 40,
        "standard_lead_time_days": 2,
        "service_level": "sl_90",
    }
    out = run_simulation(
        SimulationRequest(
            parameters=params,
            scenario="own_service_up",
            intensity=0.7,
        ),
    )
    assert out.shocked.effective_daily_demand >= out.baseline.effective_daily_demand
    assert out.plain_summary


def test_place_suggestion_model() -> None:
    p = PlaceSuggestion(
        place_id="x",
        name="GS25",
        road_address="서울 마포구 백범로 35",
        address_display="서울 마포구 백범로 35",
        score=1.2,
    )
    assert p.source == "keyword"


def test_search_dong_with_mock_returns_names() -> None:
    from app.pipeline.analyze.store_search import search_dong

    def fetch(url: str, _headers: object) -> dict[str, object]:
        if "address.json" in url:
            return {
                "documents": [
                    {
                        "address_name": "서울 마포구 신수동 1-1",
                        "address": {
                            "region_3depth_name": "신수동",
                            "address_name": "서울 마포구 신수동 1-1",
                        },
                        "road_address": {
                            "region_3depth_name": "신수동",
                            "address_name": "서울 마포구 백범로 35",
                        },
                    },
                    {
                        "address_name": "서울 마포구 대흥동 2",
                        "address": {"region_3depth_name": "대흥동"},
                    },
                ],
            }
        return {
            "documents": [
                {
                    "place_name": "카페",
                    "address_name": "서울 마포구 노고산동 10",
                    "road_address_name": "서울 마포구 백범로 1",
                },
            ],
        }

    res = search_dong(
        api_key="test",
        sido="서울특별시",
        sigungu="마포구",
        q="",
        fetch=fetch,
    )
    names = {r.name for r in res.results}
    assert "신수동" in names
    assert "대흥동" in names


def test_simulation_technical_summary_is_prose() -> None:
    params: dict[str, ParameterValue] = {
        "product_name": "생수",
        "store_type": "convenience",
        "store_size": "cv_s",
        "avg_ticket": "t_le_8k",
        "location_dong": "서울시 마포구 신수동",
        "trade_area": "campus",
        "accessibility": "main_road",
        "daily_demand": 40,
        "standard_lead_time_days": 2,
    }
    out = run_simulation(
        SimulationRequest(
            parameters=params,
            scenario="own_service_up",
            intensity=0.5,
        ),
    )
    assert "scenario=" not in out.technical_summary
    assert "D_eff" in out.technical_summary or "유효" in out.technical_summary
    assert "재발주점" in out.technical_summary or "ROP" in out.technical_summary
