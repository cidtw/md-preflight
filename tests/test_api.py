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
        "service_level",
        "order_day_pattern",
        "standard_lead_time_days",
    }.issubset(keys)
    precise = next(p for p in body["parameters"] if p["key"] == "use_precise_location")
    assert precise["type"] == "boolean"


def test_verified_demo_stores_and_survey_endpoints(client: TestClient) -> None:
    # Without Kakao key + snapshot: empty list is OK (200).
    response = client.get("/api/demo/verified-stores?live=false")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    survey = client.get("/api/demo/survey-anchor?with_context=false")
    assert survey.status_code == 200
    body = survey.json()
    assert "세솔로 25" in body["anchor_address"]
    assert "stores" in body
    assert "counts" in body

    missing = client.get("/api/demo/verified-stores/no-such-store")
    assert missing.status_code == 404


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
    assert body["recommendation_technical"]
    assert body["comparison"]["rows"]
    assert body["comparison_technical"]["rows"]
    assert len(body["evidence"]) == 4
    assert len(body["evidence_technical"]) == 4
    assert body["summary"]["product_name"] == "냉장 간편식"
    assert any(b["id"] == "geo_poi" for b in body["evidence"])
    assert any(b["id"] == "geo_poi" for b in body["evidence_technical"])
    # Technical narrative keeps specialist terms; plain stays owner-friendly.
    tech_blob = " ".join(
        p for b in body["evidence_technical"] for p in b["points"]
    ) + body["recommendation_technical"]
    assert "Z" in tech_blob or "CAPA" in tech_blob or "SS" in tech_blob


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
    """No Kakao key → still 200 with geo fallback guidance."""
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
    assert body["calc"]["geo"]["provider"] == "kakao"
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
    assert "theme-toggle" in response.text
    assert 'data-theme-btn="system"' in response.text
    assert "top-nav" in response.text
    assert "site-footer" in response.text
    assert "MD Preflight – Find ROP" in response.text  # noqa: RUF001
    assert "coming-soon" in response.text
    assert "개발자에게 제안하기" in response.text
    assert "taewon1119@gmail.com" in response.text
    # Version lives in footer, not the sticky nav.
    assert "nav-meta" not in response.text
    assert "footer-version" in response.text
    # Third-party demo readiness shell
    assert "demo-scenario-list" in response.text
    assert "세솔로 25" in response.text
    assert "verified-store-list" in response.text
    assert "demo-scenario-list" in response.text
    assert 'href="/static/favicon.svg"' in response.text
    assert 'name="description"' in response.text


def test_static_demo_assets(client: TestClient) -> None:
    for path in (
        "/static/demo_scenarios.mjs",
        "/static/favicon.svg",
        "/static/report_export.mjs",
        "/static/wizard_logic.mjs",
        "/static/store_picker.mjs",
        "/static/competition_sim.mjs",
    ):
        response = client.get(path)
        assert response.status_code == 200, path


def test_regions_sido_and_sigungu(client: TestClient) -> None:
    sido = client.get("/api/regions/sido")
    assert sido.status_code == 200
    items = sido.json()["items"]
    assert "서울특별시" in items
    sig = client.get("/api/regions/sigungu", params={"sido": "서울특별시"})
    assert sig.status_code == 200
    assert "마포구" in sig.json()["items"]


def test_places_search_without_key_ok(client: TestClient) -> None:
    """Missing Kakao key → 200 with empty results / fallback note."""
    response = client.get(
        "/api/places/search",
        params={"q": "GS25", "sido": "서울특별시", "sigungu": "마포구"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert body.get("used_fallback") is True or isinstance(body["results"], list)


def test_simulate_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/simulate",
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
            },
            "scenario": "competitor_pressure",
            "intensity": 0.6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "competitor_pressure"
    assert "baseline" in body and "shocked" in body
    assert body["shocked"]["daily_demand"] <= body["baseline"]["daily_demand"]
