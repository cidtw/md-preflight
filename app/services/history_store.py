from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Literal, Protocol

from app.schemas.history import HistoryBucket, RunHistoryRecord

HistoryGranularity = Literal["day", "month", "year"]


class HistoryStore(Protocol):
    def append(self, record: RunHistoryRecord) -> None: ...

    def query(self, user_id: str, granularity: HistoryGranularity) -> list[HistoryBucket]: ...


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


def truncate_bucket(value: datetime, granularity: HistoryGranularity) -> datetime:
    normalized = value.astimezone(UTC)
    if granularity == "year":
        return datetime(normalized.year, 1, 1, tzinfo=UTC)
    if granularity == "month":
        return datetime(normalized.year, normalized.month, 1, tzinfo=UTC)
    return datetime(normalized.year, normalized.month, normalized.day, tzinfo=UTC)


HISTORY_STORE = InMemoryHistoryStore()
