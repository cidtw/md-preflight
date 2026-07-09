from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.report import PreflightReport
from tests.test_api import build_preflight_upload_files


def test_anonymous_run_is_readable_by_anyone_via_run_id() -> None:
    client = TestClient(app)

    create = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )
    assert create.status_code == 200
    run_id = PreflightReport.model_validate(create.json()).run_id

    unauthenticated = client.get(f"/api/preflight/runs/{run_id}")
    other_user = client.get(
        f"/api/preflight/runs/{run_id}",
        headers={"x-md-preflight-user-id": "someone-else"},
    )

    assert unauthenticated.status_code == 200
    assert other_user.status_code == 200


def test_owned_run_requires_login_to_view() -> None:
    client = TestClient(app)

    create = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "owner"},
        files=build_preflight_upload_files(),
    )
    assert create.status_code == 200
    run_id = PreflightReport.model_validate(create.json()).run_id

    response = client.get(f"/api/preflight/runs/{run_id}")

    assert response.status_code == 401


def test_owned_run_rejects_other_users_with_403() -> None:
    client = TestClient(app)

    create = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "owner"},
        files=build_preflight_upload_files(),
    )
    assert create.status_code == 200
    run_id = PreflightReport.model_validate(create.json()).run_id

    response = client.get(
        f"/api/preflight/runs/{run_id}",
        headers={"x-md-preflight-user-id": "intruder"},
    )

    assert response.status_code == 403


def test_owned_run_is_readable_by_its_owner() -> None:
    client = TestClient(app)

    create = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "owner"},
        files=build_preflight_upload_files(),
    )
    assert create.status_code == 200
    run_id = PreflightReport.model_validate(create.json()).run_id

    response = client.get(
        f"/api/preflight/runs/{run_id}",
        headers={"x-md-preflight-user-id": "owner"},
    )

    assert response.status_code == 200
    assert PreflightReport.model_validate(response.json()).run_id == run_id


def test_unknown_run_returns_404_regardless_of_auth() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/preflight/runs/does-not-exist",
        headers={"x-md-preflight-user-id": "anyone"},
    )

    assert response.status_code == 404


def test_report_md_download_follows_same_authorization_matrix() -> None:
    client = TestClient(app)

    create = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "owner"},
        files=build_preflight_upload_files(),
    )
    assert create.status_code == 200
    run_id = PreflightReport.model_validate(create.json()).run_id

    no_auth = client.get(f"/api/preflight/runs/{run_id}/report.md")
    wrong_user = client.get(
        f"/api/preflight/runs/{run_id}/report.md",
        headers={"x-md-preflight-user-id": "intruder"},
    )
    owner = client.get(
        f"/api/preflight/runs/{run_id}/report.md",
        headers={"x-md-preflight-user-id": "owner"},
    )

    assert no_auth.status_code == 401
    assert wrong_user.status_code == 403
    assert owner.status_code == 200
