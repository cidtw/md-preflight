from __future__ import annotations

from enum import StrEnum
from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from app.core.errors import IngestError


class FileFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    XLS = "xls"


def detect_file_format(file_name: str) -> FileFormat:
    suffix = Path(file_name).suffix.lower().lstrip(".")
    if suffix in {FileFormat.CSV, FileFormat.XLSX, FileFormat.XLS}:
        return FileFormat(suffix)
    msg = f"Unsupported file extension for {file_name}"
    raise IngestError(msg)


def load_table(file_name: str, content: bytes) -> pd.DataFrame:
    format_ = detect_file_format(file_name)
    if format_ == FileFormat.CSV:
        return pd.read_csv(BytesIO(content))
    if format_ in {FileFormat.XLSX, FileFormat.XLS}:
        return load_excel(content)
    msg = f"Unsupported file extension for {file_name}"
    raise IngestError(msg)


def load_excel(content: bytes) -> pd.DataFrame:
    workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
    try:
        worksheet = workbook.active
        if worksheet is None:
            msg = "Workbook does not contain an active worksheet"
            raise IngestError(msg)
        rows = list(worksheet.iter_rows(values_only=True))
    finally:
        workbook.close()
    if not rows:
        return pd.DataFrame()
    headers = ["" if header is None else str(header).strip() for header in rows[0]]
    return pd.DataFrame(rows[1:], columns=headers)
