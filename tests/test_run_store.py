from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.context import PreflightContext
from app.main import app
from app.schemas.report import PreflightReport
from app.services.run_store import InMemoryRunStore, StoredRun, build_run_store
from app.services.validation_engine import validate_context
from tests.test_api import build_preflight_upload_files


def test_inmemory_run_store_round_trips_report_and_owner(
    sample_context: PreflightContext,
) -> None:
    report = validate_context(sample_context)
    store = InMemoryRunStore()

    store.save(report, owner_user_id="user-1")
    stored = store.get_stored(report.run_id)

    assert stored is not None
    assert stored.report == report
    assert stored.owner_user_id == "user-1"


def test_inmemory_run_store_defaults_owner_to_none(
    sample_context: PreflightContext,
) -> None:
    report = validate_context(sample_context)
    store = InMemoryRunStore()

    store.save(report)

    stored = store.get_stored(report.run_id)
    assert stored is not None
    assert stored.owner_user_id is None


def test_inmemory_run_store_unknown_run_id_returns_none() -> None:
    store = InMemoryRunStore()

    assert store.get_stored("does-not-exist") is None


def test_inmemory_run_store_evicts_oldest_beyond_max_items(
    sample_context: PreflightContext,
) -> None:
    store = InMemoryRunStore(max_items=1)
    first = validate_context(sample_context)
    second = validate_context(sample_context)

    store.save(first)
    store.save(second)

    assert store.get_stored(first.run_id) is None
    assert store.get_stored(second.run_id) is not None


def test_build_run_store_uses_inmemory_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "")
    get_settings.cache_clear()

    store = build_run_store()

    assert isinstance(store, InMemoryRunStore)
    get_settings.cache_clear()


def test_build_run_store_uses_postgres_when_database_url_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @dataclass
    class FakePostgresRunStore:
        database_url: str
        migration_url: str | None = None

        def __init__(self, *, database_url: str, migration_url: str | None = None) -> None:
            self.database_url = database_url
            self.migration_url = migration_url

    monkeypatch.setenv("DATABASE_URL", "postgresql://runtime")
    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "postgresql://ddl")
    monkeypatch.setattr("app.services.run_store.PostgresRunStore", FakePostgresRunStore)
    get_settings.cache_clear()

    store = build_run_store()

    assert isinstance(store, FakePostgresRunStore)
    assert store.database_url == "postgresql://runtime"
    assert store.migration_url == "postgresql://ddl"
    get_settings.cache_clear()


def test_preflight_still_returns_200_when_run_store_init_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.deps._run_store_initialized", False)
    monkeypatch.setattr("app.api.deps.run_store_instance", InMemoryRunStore())
    monkeypatch.setattr(
        "app.api.deps.build_run_store",
        lambda: (_ for _ in ()).throw(RuntimeError("db boot failed")),
    )
    client = TestClient(app)

    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )

    assert response.status_code == 200


def test_preflight_run_persistence_failure_does_not_break_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenRunStore:
        def save(self, report: PreflightReport, *, owner_user_id: str | None = None) -> None:
            del report, owner_user_id
            raise RuntimeError("save broke")

        def get_stored(self, run_id: str) -> StoredRun | None:
            del run_id
            return None

    monkeypatch.setattr("app.api.deps.run_store_instance", BrokenRunStore())
    monkeypatch.setattr("app.api.deps._run_store_initialized", True)
    client = TestClient(app)

    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )

    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())

    # Documented degrade behavior: if persistence failed, re-fetch 404s even
    # though the POST itself succeeded and returned the full report body.
    refetch = client.get(f"/api/preflight/runs/{payload.run_id}")
    assert refetch.status_code == 404
