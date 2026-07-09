from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol, cast

import psycopg
from psycopg.types.json import Json

from app.core.config import get_settings
from app.schemas.report import PreflightReport
from app.services.db import ConnectionFactory, default_connection_factory

RunRow = tuple[str, str | None, object]


@dataclass(frozen=True, slots=True)
class StoredRun:
    report: PreflightReport
    owner_user_id: str | None


class RunStore(Protocol):
    def save(self, report: PreflightReport, *, owner_user_id: str | None = None) -> None: ...

    def get_stored(self, run_id: str) -> StoredRun | None: ...


class InMemoryRunStore:
    def __init__(self, max_items: int = 128) -> None:
        self._max_items: int = max_items
        self._items: OrderedDict[str, StoredRun] = OrderedDict()

    def save(self, report: PreflightReport, *, owner_user_id: str | None = None) -> None:
        self._items[report.run_id] = StoredRun(report=report, owner_user_id=owner_user_id)
        self._items.move_to_end(report.run_id)
        while len(self._items) > self._max_items:
            _ = self._items.popitem(last=False)

    def get_stored(self, run_id: str) -> StoredRun | None:
        return self._items.get(run_id)


class PostgresRunStore:
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

    def save(self, report: PreflightReport, *, owner_user_id: str | None = None) -> None:
        with self._connect(self._database_url) as connection, connection.cursor() as cursor:
            _ = cursor.execute(
                """
                INSERT INTO preflight_runs (run_id, owner_user_id, created_at, report_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    owner_user_id = EXCLUDED.owner_user_id,
                    report_json = EXCLUDED.report_json
                """,
                (
                    report.run_id,
                    owner_user_id,
                    report.created_at,
                    Json(report.model_dump(mode="json")),
                ),
            )

    def get_stored(self, run_id: str) -> StoredRun | None:
        with self._connect(self._database_url) as connection, connection.cursor() as cursor:
            _ = cursor.execute(
                "SELECT run_id, owner_user_id, report_json FROM preflight_runs WHERE run_id = %s",
                (run_id,),
            )
            row = cast(RunRow | None, cursor.fetchone())
        if row is None:
            return None
        _run_id, owner_user_id, report_json = row
        return StoredRun(
            report=PreflightReport.model_validate(report_json),
            owner_user_id=owner_user_id,
        )

    def _ensure_schema(self) -> None:
        with self._connect(self._migration_url) as connection, connection.cursor() as cursor:
            _ = cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS preflight_runs (
                    run_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    report_json JSONB NOT NULL
                )
                """
            )

    def _connect(self, database_url: str) -> psycopg.Connection[tuple[object, ...]]:
        return self._connection_factory(database_url)


def build_run_store() -> RunStore:
    settings = get_settings()
    if settings.database_url:
        return PostgresRunStore(
            database_url=settings.database_url,
            migration_url=settings.database_url_unpooled,
        )
    return InMemoryRunStore()


RUN_STORE: RunStore = InMemoryRunStore()
