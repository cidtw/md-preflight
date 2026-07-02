from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.domain.context import PreflightContext
from app.main import app
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.report import PreflightReport
from app.schemas.rule_meta import RuleMeta


def test_validate_endpoint_when_uploading_sample_files(sample_files_dir: Path) -> None:
    client = TestClient(app)
    files = {
        "promotion_plan": (
            "promotion_plan (1).xlsx",
            (sample_files_dir / "dirty" / "promotion_plan.xlsx").read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "product_master": (
            "promo.xlsx",
            (sample_files_dir / "dirty" / "product_master.xlsx").read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "inventory": (
            "inventory copy.xlsx",
            (sample_files_dir / "dirty" / "inventory.xlsx").read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }
    response = client.post("/api/preflight/validate", files=files)
    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert payload.summary.total_issues >= 1
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
