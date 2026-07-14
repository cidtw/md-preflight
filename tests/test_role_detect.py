from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.columns import SourceFile
from app.domain.role_detect import assign_roles_greedy, score_headers_for_role, suggest_role
from app.main import app
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
