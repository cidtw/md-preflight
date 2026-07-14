from __future__ import annotations

from typing import Any

import pytest

from app.core.config import Settings
from app.core.errors import InputValidationError
from app.pipeline import run
from app.pipeline.analyze.engine import analyze
from app.pipeline.analyze.geo_enrichment import (
    compute_foot_traffic_index,
    enrich_from_address,
    map_kakao_category,
)
from app.pipeline.input.template import validate_parameters
from app.pipeline.types import NearbyPoi, ParameterValue

BASE: dict[str, ParameterValue] = {
    "product_name": "냉장 간편식",
    "store_type": "convenience",
    "store_size": "cv_s",
    "avg_ticket": "t_le_8k",
    "location_dong": "서울시 마포구 서교동",
    "trade_area": "office",
    "accessibility": "indoor",
    "daily_demand": 12,
    "standard_lead_time_days": 2,
    "standard_rop": 15,
}


def test_map_kakao_category() -> None:
    assert map_kakao_category("SW8") == "transit_rail"
    assert map_kakao_category("MT1") == "retail_anchor"
    assert map_kakao_category("XX") == "other"


def test_foot_traffic_index_increases_with_close_rail() -> None:
    empty = compute_foot_traffic_index([])
    near = compute_foot_traffic_index(
        [NearbyPoi(category="transit_rail", name="Test Station", distance_m=80.0)],
    )
    far = compute_foot_traffic_index(
        [NearbyPoi(category="transit_rail", name="Far Station", distance_m=900.0)],
    )
    assert empty == 0.0
    assert near > far > 0.0
    assert near <= 1.0


def test_precise_location_requires_address() -> None:
    with pytest.raises(InputValidationError, match="store_address"):
        _ = validate_parameters({**BASE, "use_precise_location": True})


def test_precise_false_strips_address() -> None:
    validated = validate_parameters(
        {**BASE, "use_precise_location": False, "store_address": "should drop"},
    )
    assert validated.parameters["use_precise_location"] is False
    assert "store_address" not in validated.parameters


def _mock_fetch(url: str, _headers: Any) -> dict[str, Any]:
    if "search/address.json" in url:
        return {
            "documents": [
                {
                    "address_name": "서울 마포구 양화로 45",
                    "x": "126.924",
                    "y": "37.557",
                },
            ],
        }
    if "search/category.json" in url and "SW8" in url:
        return {
            "documents": [
                {
                    "place_name": "홍대입구역",
                    "category_group_code": "SW8",
                    "distance": "90",
                    "x": "126.9245",
                    "y": "37.5575",
                },
            ],
        }
    if "search/keyword.json" in url:
        return {
            "documents": [
                {
                    "place_name": "홍대입구 버스정류장",
                    "category_group_code": "",
                    "distance": "120",
                    "x": "126.9235",
                    "y": "37.5568",
                },
            ],
        }
    if "search/category.json" in url:
        return {"documents": []}
    return {"documents": []}


def test_enrich_from_address_with_mock_kakao() -> None:
    geo = enrich_from_address(
        "서울시 마포구 양화로 45",
        api_key="test-key",
        radius_m=500,
        fetch=_mock_fetch,
    )
    assert geo.enabled is True
    assert geo.used_fallback is False
    assert geo.provider == "kakao"
    assert geo.lat is not None
    assert geo.foot_traffic_index > 0
    assert any("홍대입구역" in p.name for p in geo.pois)
    assert any(p.category == "transit_bus" for p in geo.pois)


def test_enrich_without_api_key_falls_back() -> None:
    geo = enrich_from_address("서울시 마포구 양화로 45", api_key=None)
    assert geo.enabled is True
    assert geo.used_fallback is True
    assert geo.foot_traffic_index == 0.0
    assert any("KAKAO" in n for n in geo.notes)


def test_engine_applies_foot_traffic_to_z() -> None:
    validated = validate_parameters(
        {
            **BASE,
            "use_precise_location": True,
            "store_address": "서울시 마포구 양화로 45",
        },
    )
    settings = Settings.model_validate(
        {"kakao_rest_api_key": "test-key", "geo_radius_m": 500},
    )
    with_geo = analyze(validated, settings=settings, geo_fetch=_mock_fetch)
    without = analyze(
        validate_parameters(BASE),
        settings=Settings.model_validate({"kakao_rest_api_key": None}),
    )
    assert with_geo.geo.foot_traffic_index > 0
    assert with_geo.knowledge.safety_z_factor > without.knowledge.safety_z_factor
    assert with_geo.store_safety_stock >= without.store_safety_stock
    assert with_geo.geo.used_fallback is False
    assert with_geo.geo.provider == "kakao"


def test_run_without_precise_still_has_geo_block() -> None:
    result = run(BASE)
    ids = [b.id for b in result.evidence]
    assert "geo_poi" in ids
    assert result.calc.geo.enabled is False
