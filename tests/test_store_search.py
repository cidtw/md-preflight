"""Unit tests for place ranking and competition simulation (no live Kakao)."""

from __future__ import annotations

from app.pipeline.analyze.competition_sim import SimulationRequest, run_simulation
from app.pipeline.analyze.store_search import (
    PlaceSuggestion,
    _similarity,
    search_places,
)
from app.pipeline.region_catalog import list_sido, list_sigungu, region_prefix
from app.pipeline.types import ParameterValue


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
