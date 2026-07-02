from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.ingest.loader import detect_file_format, load_table


def test_detect_file_format_when_csv() -> None:
    assert detect_file_format("promotion_plan.csv") == "csv"


def test_load_table_when_excel(sample_files_dir: Path) -> None:
    frame = load_table(
        str(sample_files_dir / "clean" / "promotion_plan.xlsx"),
        (sample_files_dir / "clean" / "promotion_plan.xlsx").read_bytes(),
    )
    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == [
        "promotion_id",
        "product_code",
        "start_date",
        "end_date",
        "promo_price",
        "benefit_type",
        "benefit_condition",
    ]
