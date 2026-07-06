from __future__ import annotations

from typing import Protocol, TypeAlias

import pandas as pd

from app.schemas.source_meta import SourceMeta, SourceStatus

LoadedTable: TypeAlias = pd.DataFrame


class TabularSource(Protocol):
    def fetch(self) -> LoadedTable: ...


SOURCE_CATALOG: list[SourceMeta] = [
    SourceMeta(
        id="upload",
        label="파일 업로드",
        description="CSV 또는 XLSX 파일을 직접 업로드합니다.",
        auth_fields=[],
        status=SourceStatus.AVAILABLE,
    ),
    SourceMeta(
        id="notion",
        label="Notion",
        description="Notion 데이터베이스에서 프로모션 데이터를 바로 불러오는 경로입니다.",
        auth_fields=["integration token", "database id"],
        status=SourceStatus.PLANNED,
    ),
    SourceMeta(
        id="google_sheets",
        label="Google Sheets",
        description="Google Sheets 문서 URL 또는 시트 식별자로 데이터를 가져오는 경로입니다.",
        auth_fields=["sheet url or spreadsheet id", "access token"],
        status=SourceStatus.PLANNED,
    ),
    SourceMeta(
        id="csv_url",
        label="CSV URL",
        description="외부 CSV URL에서 데이터를 읽어오는 경로입니다.",
        auth_fields=["csv url", "optional auth header"],
        status=SourceStatus.PLANNED,
    ),
]
