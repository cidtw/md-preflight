from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["pipeline"] == "input-analyze-output"


def test_template(client: TestClient) -> None:
    response = client.get("/api/template")
    assert response.status_code == 200
    body = response.json()
    keys = {p["key"] for p in body["parameters"]}
    assert {"quality", "cost", "risk"}.issubset(keys)


def test_evaluate_ok(client: TestClient) -> None:
    response = client.post(
        "/api/evaluate",
        json={"parameters": {"quality": 80, "cost": 40, "risk": 30}},
    )
    assert response.status_code == 200
    body = response.json()
    assert "recommendation" in body
    assert body["band"] in {"strong", "moderate", "weak"}
    assert 0.0 <= body["score"] <= 1.0


def test_evaluate_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/evaluate",
        json={"parameters": {"quality": 80}},
    )
    assert response.status_code == 400
    assert "Missing" in response.json()["detail"]


def test_index_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Input → Analyze → Output" in response.text
