from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal, Protocol, cast

import psycopg
from psycopg.types.json import Json

from app.core.config import get_settings
from app.schemas.history import HistoryBucket, RuleTrigger, RunHistoryRecord
from app.services.db import ConnectionFactory, default_connection_factory

HistoryGranularity = Literal["day", "month", "year"]
HistoryAggregateRow = tuple[datetime, int, int, int, float]
RunRow = tuple[int, str, str, datetime, bool, int, int, int, str | None, object, str | None]
JsonRuleTrigger = dict[str, str | int]


class HistoryStore(Protocol):
    def append(self, record: RunHistoryRecord) -> None: ...

    def query(self, user_id: str, granularity: HistoryGranularity) -> list[HistoryBucket]: ...

    def list_runs(self, user_id: str, *, limit: int) -> list[RunHistoryRecord]: ...


class InMemoryHistoryStore:
    def __init__(self) -> None:
        self._records: list[RunHistoryRecord] = []

    def append(self, record: RunHistoryRecord) -> None:
        self._records.append(record)

    def query(self, user_id: str, granularity: HistoryGranularity) -> list[HistoryBucket]:
        grouped: dict[datetime, list[RunHistoryRecord]] = defaultdict(list)
        for record in self._records:
            if record.user_id != user_id:
                continue
            grouped[truncate_bucket(record.created_at, granularity)].append(record)
        return [
            HistoryBucket(
                bucket=bucket,
                run_count=len(records),
                error_total=sum(record.error_count for record in records),
                warning_total=sum(record.warning_count for record in records),
                passed_rate=sum(1 for record in records if record.passed) / len(records),
            )
            for bucket, records in sorted(grouped.items())
        ]

    def list_runs(self, user_id: str, *, limit: int) -> list[RunHistoryRecord]:
        return sorted(
            (record for record in self._records if record.user_id == user_id),
            key=lambda record: record.created_at,
            reverse=True,
        )[:limit]


class PostgresHistoryStore:
    _database_url: str
    _migration_url: str
    _connection_factory: ConnectionFactory

    def __init__(
        self,
        *,
        database_url: str,
        migration_url: str | None = None,
        connection_factory: ConnectionFactory = default_connection_factory,
    ) -> None:
        self._database_url = database_url
        self._migration_url = migration_url or database_url
        self._connection_factory = connection_factory
        self._ensure_schema()

    def append(self, record: RunHistoryRecord) -> None:
        with self._connect(self._database_url) as connection, connection.cursor() as cursor:
            _ = cursor.execute(
                """
                INSERT INTO run_history (
                    user_id,
                    run_id,
                    created_at,
                    passed,
                    error_count,
                    warning_count,
                    total_issues,
                    source_label,
                    rules_triggered,
                    rule_set_version
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record.user_id,
                    record.run_id,
                    record.created_at,
                    record.passed,
                    record.error_count,
                    record.warning_count,
                    record.total_issues,
                    record.source_label,
                    Json(serialize_rule_triggers(record.rules_triggered)),
                    record.rule_set_version,
                ),
            )

    def query(self, user_id: str, granularity: HistoryGranularity) -> list[HistoryBucket]:
        with self._connect(self._database_url) as connection, connection.cursor() as cursor:
            _ = cursor.execute(
                """
                SELECT
                    date_trunc(%s, created_at AT TIME ZONE 'UTC') AT TIME ZONE 'UTC' AS bucket,
                    COUNT(*)::int AS run_count,
                    COALESCE(SUM(error_count), 0)::int AS error_total,
                    COALESCE(SUM(warning_count), 0)::int AS warning_total,
                    AVG(CASE WHEN passed THEN 1.0 ELSE 0.0 END)::float8 AS passed_rate
                FROM run_history
                WHERE user_id = %s
                GROUP BY bucket
                ORDER BY bucket ASC
                """,
                (granularity, user_id),
            )
            rows = cast(Sequence[HistoryAggregateRow], cursor.fetchall())
        return [
            HistoryBucket(
                bucket=ensure_utc_datetime(bucket),
                run_count=run_count,
                error_total=error_total,
                warning_total=warning_total,
                passed_rate=passed_rate,
            )
            for bucket, run_count, error_total, warning_total, passed_rate in rows
        ]

    def list_runs(self, user_id: str, *, limit: int) -> list[RunHistoryRecord]:
        with self._connect(self._database_url) as connection, connection.cursor() as cursor:
            _ = cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    run_id,
                    created_at,
                    passed,
                    error_count,
                    warning_count,
                    total_issues,
                    source_label,
                    rules_triggered,
                    rule_set_version
                FROM run_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cast(Sequence[RunRow], cursor.fetchall())
        return [record_from_row(row) for row in rows]

    def _ensure_schema(self) -> None:
        with self._connect(self._migration_url) as connection, connection.cursor() as cursor:
            _ = cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS run_history (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    passed BOOLEAN NOT NULL,
                    error_count INTEGER NOT NULL,
                    warning_count INTEGER NOT NULL,
                    total_issues INTEGER NOT NULL,
                    source_label TEXT NULL,
                    rules_triggered JSONB NOT NULL DEFAULT '[]'::jsonb,
                    rule_set_version TEXT NULL
                )
                """
            )
            _ = cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS run_history_user_created_idx
                ON run_history (user_id, created_at DESC)
                """
            )
            # Idempotent migration for tables created before rule_set_version existed.
            _ = cursor.execute(
                """
                ALTER TABLE run_history
                ADD COLUMN IF NOT EXISTS rule_set_version TEXT NULL
                """
            )

    def _connect(self, database_url: str) -> psycopg.Connection[tuple[object, ...]]:
        return self._connection_factory(database_url)


def build_history_store() -> HistoryStore:
    settings = get_settings()
    if settings.database_url:
        return PostgresHistoryStore(
            database_url=settings.database_url,
            migration_url=settings.database_url_unpooled,
        )
    return InMemoryHistoryStore()


def serialize_rule_triggers(triggers: Sequence[RuleTrigger]) -> list[JsonRuleTrigger]:
    return [
        {
            "code": trigger.code,
            "severity": trigger.severity.value,
            "count": trigger.count,
        }
        for trigger in triggers
    ]


def deserialize_rule_triggers(payload: object) -> list[RuleTrigger]:
    if not isinstance(payload, list):
        return []
    validated: list[RuleTrigger] = []
    for item in cast(list[object], payload):
        if isinstance(item, dict):
            validated.append(RuleTrigger.model_validate(item))
    return validated


def record_from_row(row: RunRow) -> RunHistoryRecord:
    (
        record_id,
        user_id,
        run_id,
        created_at,
        passed,
        error_count,
        warning_count,
        total_issues,
        source_label,
        rules_triggered,
        rule_set_version,
    ) = row
    return RunHistoryRecord(
        id=record_id,
        user_id=user_id,
        run_id=run_id,
        created_at=ensure_utc_datetime(created_at),
        passed=passed,
        error_count=error_count,
        warning_count=warning_count,
        total_issues=total_issues,
        source_label=source_label,
        rules_triggered=deserialize_rule_triggers(rules_triggered),
        rule_set_version=rule_set_version,
    )


def ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def truncate_bucket(value: datetime, granularity: HistoryGranularity) -> datetime:
    normalized = value.astimezone(UTC)
    if granularity == "year":
        return datetime(normalized.year, 1, 1, tzinfo=UTC)
    if granularity == "month":
        return datetime(normalized.year, normalized.month, 1, tzinfo=UTC)
    return datetime(normalized.year, normalized.month, normalized.day, tzinfo=UTC)


HISTORY_STORE: HistoryStore = InMemoryHistoryStore()
