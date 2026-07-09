from __future__ import annotations

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.core.config import Settings, get_settings
from app.main import app


def build_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode(), value.encode()) for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "headers": raw_headers,
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "server": ("test", 80),
        "client": ("test", 123),
        "scheme": "http",
    }
    return Request(scope)


def test_auth_mode_is_off_by_default() -> None:
    settings = Settings.model_construct(
        clerk_secret_key=None,
        clerk_publishable_key=None,
        allow_stub_auth=False,
    )
    assert settings.auth_mode == "off"


def test_auth_mode_is_stub_when_explicitly_enabled() -> None:
    settings = Settings.model_construct(
        clerk_secret_key=None,
        clerk_publishable_key=None,
        allow_stub_auth=True,
    )
    assert settings.auth_mode == "stub"


def test_auth_mode_prefers_clerk_over_stub() -> None:
    settings = Settings.model_construct(
        clerk_secret_key="sk_test_x",
        clerk_publishable_key="pk_test_x",
        allow_stub_auth=True,
    )
    assert settings.auth_mode == "clerk"


def test_get_current_user_id_ignores_stub_header_when_auth_mode_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MDPREFLIGHT_ALLOW_STUB_AUTH", raising=False)
    get_settings.cache_clear()

    request = build_request({"x-md-preflight-user-id": "user-123"})

    assert get_current_user_id(request) is None
    get_settings.cache_clear()


def test_get_current_user_id_honors_stub_header_when_explicitly_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MDPREFLIGHT_ALLOW_STUB_AUTH", "true")
    get_settings.cache_clear()

    request = build_request({"x-md-preflight-user-id": "user-123"})

    assert get_current_user_id(request) == "user-123"
    get_settings.cache_clear()


def test_history_endpoint_401_with_spoofed_stub_header_when_stub_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MDPREFLIGHT_ALLOW_STUB_AUTH", raising=False)
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(
        "/api/preflight/history",
        headers={"x-md-preflight-user-id": "attacker-controlled"},
    )

    assert response.status_code == 401
    get_settings.cache_clear()
