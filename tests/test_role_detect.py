from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.columns import SourceFile
from app.domain.role_detect import assign_roles_greedy, score_headers_for_role, suggest_role
from app.main import app
from app.schemas.report import PreflightReport
from app.schemas.role_detect import DetectRolesResponse


def test_score_prefers_promotion_headers() -> None:
    headers = [
        "promotion_id",
        "product_code",
        "start_date",
        "end_date",
        "promo_price",
        "benefit_type",
        "benefit_condition",
    ]
    promo = score_headers_for_role(headers, SourceFile.PROMOTION_PLAN)
    master = score_headers_for_role(headers, SourceFile.PRODUCT_MASTER)
    assert promo.score > master.score
    assert suggest_role(headers).suggested_role == SourceFile.PROMOTION_PLAN


def test_score_accepts_korean_inventory_headers() -> None:
    headers = ["상품코드", "재고수량", "입고예정일", "예상수요"]
    suggestion = suggest_role(headers)
    assert suggestion.suggested_role == SourceFile.INVENTORY
    assert suggestion.confidence >= 0.5


def test_assign_roles_greedy_unique() -> None:
    artifacts = [
        (
            "p",
            [
                "행사코드",
                "상품코드",
                "시작일",
                "종료일",
                "행사가",
                "혜택유형",
                "혜택조건",
            ],
        ),
        ("m", ["SKU", "품명", "정상가", "원가"]),
        ("i", ["상품코드", "재고수량", "입고예정일", "예상수요"]),
    ]
    assignment = assign_roles_greedy(artifacts)
    assert assignment["p"] == SourceFile.PROMOTION_PLAN
    assert assignment["m"] == SourceFile.PRODUCT_MASTER
    assert assignment["i"] == SourceFile.INVENTORY


def test_expand_multisheet_workbook(sample_files_dir: Path) -> None:
    from app.ingest.loader import expand_upload_tables

    path = sample_files_dir / "multisheet" / "preflight_bundle.xlsx"
    tables = expand_upload_tables(path.name, path.read_bytes())
    assert len(tables) == 3
    names = {table.sheet_name for table in tables}
    assert names == {"행사계획", "상품마스터", "재고"}
    assignment = assign_roles_greedy(
        [(table.label, table.headers) for table in tables]
    )
    roles = set(assignment.values())
    assert SourceFile.PROMOTION_PLAN in roles
    assert SourceFile.PRODUCT_MASTER in roles
    assert SourceFile.INVENTORY in roles


def test_detect_roles_api_on_alias_samples(sample_files_dir: Path) -> None:
    client = TestClient(app)
    alias = sample_files_dir / "alias_ko"
    files = [
        (
            "files",
            (
                "promotion_plan.csv",
                (alias / "promotion_plan.csv").read_bytes(),
                "text/csv",
            ),
        ),
        (
            "files",
            (
                "product_master.csv",
                (alias / "product_master.csv").read_bytes(),
                "text/csv",
            ),
        ),
        (
            "files",
            (
                "inventory.csv",
                (alias / "inventory.csv").read_bytes(),
                "text/csv",
            ),
        ),
    ]

    response = client.post("/api/preflight/detect-roles", files=files)

    assert response.status_code == 200
    payload = DetectRolesResponse.model_validate(response.json())
    assert len(payload.artifacts) == 3
    assigned = {item.filename: item.assigned_role for item in payload.artifacts}
    assert assigned["promotion_plan.csv"] == "promotion_plan"
    assert assigned["product_master.csv"] == "product_master"
    assert assigned["inventory.csv"] == "inventory"
    assert payload.frames_ready["promotion_plan"] is True
    assert payload.frames_ready["product_master"] is True
    assert payload.frames_ready["inventory"] is True


def test_detect_roles_api_splits_multisheet(sample_files_dir: Path) -> None:
    client = TestClient(app)
    path = sample_files_dir / "multisheet" / "preflight_bundle.xlsx"
    response = client.post(
        "/api/preflight/detect-roles",
        files=[
            (
                "files",
                ("preflight_bundle.xlsx", path.read_bytes(),
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            )
        ],
    )
    assert response.status_code == 200
    payload = DetectRolesResponse.model_validate(response.json())
    assert len(payload.artifacts) == 3
    assert all(item.sheet_name for item in payload.artifacts)
    assert all(item.source_filename == "preflight_bundle.xlsx" for item in payload.artifacts)
    assigned = {item.assigned_role for item in payload.artifacts}
    assert assigned == {"promotion_plan", "product_master", "inventory"}


def test_preflight_with_sheet_selectors_and_role_mappings(sample_files_dir: Path) -> None:
    client = TestClient(app)
    path = sample_files_dir / "multisheet" / "preflight_bundle.xlsx"
    content = path.read_bytes()
    media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    role_mappings = [
        {
            "frame": "promotion_plan",
            "source_filename": "preflight_bundle.xlsx",
            "sheet_name": "행사계획",
            "label": "preflight_bundle.xlsx · 행사계획",
            "confidence": 0.9,
            "suggested_role": "promotion_plan",
            "confirmed": True,
        },
        {
            "frame": "product_master",
            "source_filename": "preflight_bundle.xlsx",
            "sheet_name": "상품마스터",
            "label": "preflight_bundle.xlsx · 상품마스터",
            "confidence": 0.9,
            "suggested_role": "product_master",
            "confirmed": True,
        },
        {
            "frame": "inventory",
            "source_filename": "preflight_bundle.xlsx",
            "sheet_name": "재고",
            "label": "preflight_bundle.xlsx · 재고",
            "confidence": 0.9,
            "suggested_role": "inventory",
            "confirmed": True,
        },
    ]
    response = client.post(
        "/api/preflight/validate",
        data={
            "promotion_sheet": "행사계획",
            "product_sheet": "상품마스터",
            "inventory_sheet": "재고",
            "role_mappings": json.dumps(role_mappings, ensure_ascii=False),
        },
        files={
            "promotion_plan": ("preflight_bundle.xlsx", content, media),
            "product_master": ("preflight_bundle.xlsx", content, media),
            "inventory": ("preflight_bundle.xlsx", content, media),
        },
    )
    assert response.status_code == 200
    report = PreflightReport.model_validate(response.json())
    assert report.summary.total_issues >= 9
    assert len(report.role_mappings) == 3
    assert {item.frame for item in report.role_mappings} == {
        "promotion_plan",
        "product_master",
        "inventory",
    }
    assert report.role_mappings[0].sheet_name in {"행사계획", "상품마스터", "재고"}
    md = client.get(f"/api/preflight/runs/{report.run_id}/report.md")
    assert md.status_code == 200
    assert "Role Mapping" in md.text
