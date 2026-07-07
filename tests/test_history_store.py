from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.core.config import get_settings
from app.domain.context import PreflightContext
from app.schemas.history import RuleTrigger, RunHistoryRecord
from app.schemas.issue import Severity
from app.services.history_store import (
    InMemoryHistoryStore,
    build_history_store,
    deserialize_rule_triggers,
    record_from_row,
    serialize_rule_triggers,
)
from app.services.validation_engine import validate_context


def test_run_history_record_from_report_uses_aggregate_fields(
    sample_context: PreflightContext,
) -> None:
    report = validate_context(sample_context)

    record = RunHistoryRecord.from_report("user-1", report.run_id, report)

    assert record.user_id == "user-1"
    assert record.run_id == report.run_id
    assert record.error_count == report.summary.by_severity["error"]
    assert record.warning_count == report.summary.by_severity["warning"]
    assert record.total_issues == report.summary.total_issues
    assert {item.code: item.count for item in record.rules_triggered} == report.summary.by_rule


def test_inmemory_history_store_groups_day_month_year() -> None:
    store = InMemoryHistoryStore()
    store.append(
        RunHistoryRecord(
            user_id="user-1",
            run_id="run-1",
            created_at=datetime(2026, 7, 6, 9, 0, tzinfo=UTC),
            passed=False,
            error_count=2,
            warning_count=3,
            total_issues=5,
            rules_triggered=[],
        )
    )
    store.append(
        RunHistoryRecord(
            user_id="user-1",
            run_id="run-2",
            created_at=datetime(2026, 7, 6, 17, 0, tzinfo=UTC),
            passed=True,
            error_count=0,
            warning_count=1,
            total_issues=1,
            rules_triggered=[],
        )
    )
    store.append(
        RunHistoryRecord(
            user_id="user-1",
            run_id="run-3",
            created_at=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
            passed=True,
            error_count=0,
            warning_count=0,
            total_issues=0,
            rules_triggered=[],
        )
    )

    day_buckets = store.query("user-1", "day")
    month_buckets = store.query("user-1", "month")
    year_buckets = store.query("user-1", "year")

    assert len(day_buckets) == 2
    assert day_buckets[0].run_count == 2
    assert day_buckets[0].error_total == 2
    assert day_buckets[0].warning_total == 4
    assert day_buckets[0].passed_rate == 0.5
    assert len(month_buckets) == 2
    assert month_buckets[0].run_count == 2
    assert len(year_buckets) == 1
    assert year_buckets[0].run_count == 3


def test_inmemory_history_store_lists_runs_latest_first() -> None:
    store = InMemoryHistoryStore()
    store.append(
        RunHistoryRecord(
            user_id="user-1",
            run_id="run-1",
            created_at=datetime(2026, 7, 6, 9, 0, tzinfo=UTC),
            passed=False,
            error_count=2,
            warning_count=3,
            total_issues=5,
            rules_triggered=[],
        )
    )
    store.append(
        RunHistoryRecord(
            user_id="user-1",
            run_id="run-2",
            created_at=datetime(2026, 7, 6, 17, 0, tzinfo=UTC),
            passed=True,
            error_count=0,
            warning_count=1,
            total_issues=1,
            rules_triggered=[],
        )
    )

    runs = store.list_runs("user-1", limit=1)

    assert [run.run_id for run in runs] == ["run-2"]


def test_rule_trigger_round_trip_preserves_severity() -> None:
    triggers = [
        RuleTrigger(code="LOW_MARGIN_RATE", severity=Severity.WARNING, count=2),
        RuleTrigger(code="INVALID_PROMO_PRICE", severity=Severity.ERROR, count=1),
    ]

    payload = serialize_rule_triggers(triggers)
    restored = deserialize_rule_triggers(payload)

    assert restored == triggers


def test_record_from_postgres_row_parses_json_payload() -> None:
    record = record_from_row(
        (
            7,
            "user-1",
            "run-7",
            datetime(2026, 7, 7, 9, 30, tzinfo=UTC),
            False,
            2,
            1,
            3,
            "upload",
            [
                {"code": "LOW_MARGIN_RATE", "severity": "warning", "count": 1},
                {"code": "INVALID_PROMO_PRICE", "severity": "error", "count": 2},
            ],
        )
    )

    assert record.id == 7
    assert record.user_id == "user-1"
    assert [rule.code for rule in record.rules_triggered] == [
        "LOW_MARGIN_RATE",
        "INVALID_PROMO_PRICE",
    ]


def test_build_history_store_uses_inmemory_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "")
    get_settings.cache_clear()

    store = build_history_store()

    assert isinstance(store, InMemoryHistoryStore)


def test_build_history_store_uses_postgres_when_database_url_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @dataclass
    class FakePostgresHistoryStore:
        database_url: str
        migration_url: str | None = None

        def __init__(self, *, database_url: str, migration_url: str | None = None) -> None:
            self.database_url = database_url
            self.migration_url = migration_url

    monkeypatch.setenv("DATABASE_URL", "postgresql://runtime")
    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "postgresql://ddl")
    monkeypatch.setattr("app.services.history_store.PostgresHistoryStore", FakePostgresHistoryStore)
    get_settings.cache_clear()

    store = build_history_store()

    assert isinstance(store, FakePostgresHistoryStore)
    assert store.database_url == "postgresql://runtime"
    assert store.migration_url == "postgresql://ddl"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
