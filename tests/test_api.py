from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.domain.context import PreflightContext
from app.main import app
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.report import PreflightReport
from app.schemas.rule_meta import RuleMeta
from tests.conftest import (
    build_sample_inventory,
    build_sample_products,
    build_sample_promotions,
)


def frame_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode()


def test_validate_endpoint_when_uploading_sample_files() -> None:
    client = TestClient(app)
    files = {
        "promotion_plan": (
            "promotion_plan.csv",
            frame_to_csv_bytes(build_sample_promotions()),
            "text/csv",
        ),
        "product_master": (
            "product_master.csv",
            frame_to_csv_bytes(build_sample_products()),
            "text/csv",
        ),
        "inventory": (
            "inventory.csv",
            frame_to_csv_bytes(build_sample_inventory()),
            "text/csv",
        ),
    }
    response = client.post("/api/preflight/validate", files=files)
    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert payload.summary.total_issues == 9
    assert payload.summary.by_rule == {
        "INVALID_DATE_RANGE": 1,
        "INVALID_PROMO_PRICE": 1,
        "EXTREME_DISCOUNT_RATE": 1,
        "LOW_MARGIN_RATE": 2,
        "MISSING_PRODUCT_MASTER": 1,
        "INVENTORY_SHORTAGE_RISK": 1,
        "INBOUND_DATE_CONFLICT": 1,
        "MISSING_BENEFIT_CONDITION": 1,
    }
    run_id = payload.run_id
    assert payload.failed_rules == []
    stored = client.get(f"/api/preflight/runs/{run_id}")
    assert stored.status_code == 200
    stored_payload = PreflightReport.model_validate(stored.json())
    assert stored_payload.run_id == run_id


def test_rules_endpoint_returns_registry() -> None:
    client = TestClient(app)
    response = client.get("/api/preflight/rules")
    assert response.status_code == 200
    rules = TypeAdapter(list[RuleMeta]).validate_python(response.json())
    codes = [rule.code for rule in rules]
    assert codes == [
        "INVALID_DATE_RANGE",
        "MISSING_PRODUCT_MASTER",
        "INVALID_PROMO_PRICE",
        "EXTREME_DISCOUNT_RATE",
        "LOW_MARGIN_RATE",
        "INVENTORY_SHORTAGE_RISK",
        "INBOUND_DATE_CONFLICT",
        "MISSING_BENEFIT_CONDITION",
    ]


def test_validate_endpoint_reports_failed_rules_when_a_rule_raises(
    sample_files_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)

    class BrokenRule:
        code: str = "BROKEN_RULE"
        severity: Severity = Severity.WARNING
        description: str = "broken"

        def apply(self, _ctx: PreflightContext) -> list[ValidationIssue]:
            raise RuntimeError("boom")

        def meta(self) -> RuleMeta:
            return RuleMeta(code=self.code, severity=self.severity, description=self.description)

    monkeypatch.setattr("app.services.validation_engine.RULES", [BrokenRule()])
    files = {
        "promotion_plan": (
            "promotion_plan.csv",
            (sample_files_dir / "dirty" / "promotion_plan.csv").read_bytes(),
            "text/csv",
        ),
        "product_master": (
            "product_master.csv",
            (sample_files_dir / "dirty" / "product_master.csv").read_bytes(),
            "text/csv",
        ),
        "inventory": (
            "inventory.csv",
            (sample_files_dir / "dirty" / "inventory.csv").read_bytes(),
            "text/csv",
        ),
    }
    response = client.post("/api/preflight/validate", files=files)
    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert payload.failed_rules == ["BROKEN_RULE"]
