from datetime import UTC, datetime

from app.schemas.issue import IssueLocation, Severity, ValidationIssue
from app.schemas.report import GenerationSource, PreflightReport, PreflightSummary
from app.services.llm_service import build_fallback_narrative
from app.services.report_service import render_markdown_report


def test_build_fallback_narrative_when_issues_exist() -> None:
    issues = [
        ValidationIssue(
            code="INVALID_PROMO_PRICE",
            severity=Severity.ERROR,
            title="행사가가 유효하지 않습니다",
            message="프로모션 가격을 확인하세요.",
            entity={"promotion_id": "P-1", "product_code": "SKU-1"},
            location=IssueLocation(file="promotion_plan", row=2, column="promo_price"),
            observed="promo_price=12000",
            expected="0 < promo_price <= normal_price",
            suggestion="행사가를 수정하세요.",
        )
    ]
    narrative = build_fallback_narrative(issues)
    assert "총 1건의 이슈가 발견되었습니다." in narrative.ai_summary
    assert narrative.checklist == ["[INVALID_PROMO_PRICE] 행사가를 수정하세요."]


def test_render_markdown_report_when_report_exists() -> None:
    report = PreflightReport(
        run_id="run-1",
        summary=PreflightSummary(
            total_issues=1,
            by_severity={"error": 1, "warning": 0, "info": 0},
            by_rule={"INVALID_PROMO_PRICE": 1},
            passed=False,
            checked_rows=6,
        ),
        issues=[
            ValidationIssue(
                code="INVALID_PROMO_PRICE",
                severity=Severity.ERROR,
                title="행사가가 유효하지 않습니다",
                message="프로모션 가격을 확인하세요.",
                entity={"promotion_id": "P-1", "product_code": "SKU-1"},
                location=IssueLocation(file="promotion_plan", row=2, column="promo_price"),
                observed="promo_price=12000",
                expected="0 < promo_price <= normal_price",
                suggestion="행사가를 수정하세요.",
            )
        ],
        ai_summary="총 1건의 이슈가 발견되었습니다.",
        checklist=["[INVALID_PROMO_PRICE] 행사가를 수정하세요."],
        generated_by=GenerationSource.FALLBACK,
        created_at=datetime(2026, 7, 6, 14, 32, tzinfo=UTC),
    )
    markdown = render_markdown_report(report)
    assert "# MD Preflight Report" in markdown
    assert "INVALID_PROMO_PRICE" in markdown
    assert "행사가를 수정하세요." in markdown
