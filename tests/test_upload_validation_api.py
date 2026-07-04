from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.main import app
from tests.conftest import build_sample_promotions
from tests.test_api import build_preflight_upload_files


def _post_endpoint(
    client: TestClient,
    endpoint: str,
    files: dict[str, tuple[str, bytes, str]],
) -> int:
    response = client.post(
        endpoint,
        data={"use_llm": "false"} if endpoint == "/api/preflight" else None,
        files=files,
    )
    return response.status_code


@pytest.mark.parametrize("endpoint", ["/api/preflight", "/api/preflight/validate"])
def test_rejects_bad_extension_400(endpoint: str) -> None:
    client = TestClient(app)
    files = build_preflight_upload_files()
    files["promotion_plan"] = ("promotion_plan.txt", files["promotion_plan"][1], "text/plain")

    assert _post_endpoint(client, endpoint, files) == 400


@pytest.mark.parametrize("endpoint", ["/api/preflight", "/api/preflight/validate"])
def test_rejects_oversized_file_413(endpoint: str) -> None:
    client = TestClient(app)
    app.dependency_overrides[get_app_settings] = lambda: Settings(max_upload_bytes=8)
    try:
        assert _post_endpoint(client, endpoint, build_preflight_upload_files()) == 413
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("endpoint", ["/api/preflight", "/api/preflight/validate"])
def test_valid_upload_still_200(endpoint: str) -> None:
    client = TestClient(app)

    assert _post_endpoint(client, endpoint, build_preflight_upload_files()) == 200


@pytest.mark.parametrize("endpoint", ["/api/preflight", "/api/preflight/validate"])
def test_missing_column_still_422(endpoint: str) -> None:
    client = TestClient(app)
    promotions = build_sample_promotions().drop(columns=["benefit_condition"])

    assert (
        _post_endpoint(
            client,
            endpoint,
            build_preflight_upload_files(promotions=promotions),
        )
        == 422
    )
