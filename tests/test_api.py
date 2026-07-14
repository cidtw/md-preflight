from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "rop-adjust"


def test_template_has_rop_fields(client: TestClient) -> None:
    response = client.get("/api/template")
    assert response.status_code == 200
    body = response.json()
    keys = {p["key"] for p in body["parameters"]}
    assert {
        "product_name",
        "store_type",
        "store_size",
        "avg_ticket",
        "location_dong",
        "use_precise_location",
        "store_address",
        "trade_area",
        "accessibility",
        "daily_demand",
    }.issubset(keys)
    precise = next(p for p in body["parameters"] if p["key"] == "use_precise_location")
    assert precise["type"] == "boolean"


def test_evaluate_ok(client: TestClient) -> None:
    response = client.post(
        "/api/evaluate",
        json={
            "parameters": {
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
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "recommendation" in body
    assert body["comparison"]["rows"]
    assert len(body["evidence"]) == 4
    assert body["summary"]["product_name"] == "냉장 간편식"
    assert any(b["id"] == "geo_poi" for b in body["evidence"])


def test_evaluate_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/evaluate",
        json={"parameters": {"product_name": "x"}},
    )
    assert response.status_code == 400


def test_evaluate_precise_without_address(client: TestClient) -> None:
    response = client.post(
        "/api/evaluate",
        json={
            "parameters": {
                "product_name": "냉장 간편식",
                "store_type": "convenience",
                "store_size": "cv_s",
                "avg_ticket": "t_le_8k",
                "location_dong": "서울시 마포구 서교동",
                "use_precise_location": True,
                "trade_area": "office",
                "accessibility": "indoor",
                "daily_demand": 12,
            }
        },
    )
    assert response.status_code == 400
    assert "store_address" in response.json()["detail"]


def test_evaluate_precise_without_key_falls_back(client: TestClient) -> None:
    """No API key → still 200 with geo fallback guidance."""
    response = client.post(
        "/api/evaluate",
        json={
            "parameters": {
                "product_name": "냉장 간편식",
                "store_type": "convenience",
                "store_size": "cv_s",
                "avg_ticket": "t_le_8k",
                "location_dong": "서울시 마포구 서교동",
                "use_precise_location": True,
                "store_address": "서울시 마포구 양화로 45",
                "trade_area": "office",
                "accessibility": "indoor",
                "daily_demand": 12,
                "standard_lead_time_days": 2,
                "standard_rop": 15,
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["calc"]["geo"]["enabled"] is True
    assert body["calc"]["geo"]["used_fallback"] is True
    assert any(b["id"] == "geo_poi" for b in body["evidence"])


def test_index_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "ROP" in response.text
    # Multi-session wizard shell
    assert "step-welcome" in response.text
    assert "매장 기본 정보" in response.text
    assert "매장 세부 정보" in response.text
    assert "품목 · 운영 기준" in response.text
