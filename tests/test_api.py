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
        "trade_area",
        "accessibility",
        "daily_demand",
    }.issubset(keys)


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
    assert len(body["evidence"]) == 3
    assert body["summary"]["product_name"] == "냉장 간편식"


def test_evaluate_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/evaluate",
        json={"parameters": {"product_name": "x"}},
    )
    assert response.status_code == 400


def test_index_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "ROP" in response.text
    # Multi-session wizard shell
    assert "step-welcome" in response.text
    assert "매장 기본 정보" in response.text
    assert "매장 세부 정보" in response.text
    assert "품목 · 운영 기준" in response.text
