from datetime import UTC, datetime

from app.core.rule_config import RuleThresholds
from app.ingest.normalize import build_context
from app.schemas.issue import IssueLocation, Severity, ValidationIssue
from app.schemas.report import FileSummary, GenerationSource, PreflightReport, PreflightSummary
from app.services.checklist_service import build_checklist_items
from app.services.llm_service import (
    FileIssueGroup,
    build_fallback_narrative,
    merge_llm_file_summaries,
)
from app.services.report_service import render_markdown_report
from tests.conftest import build_sample_inventory, build_sample_products, build_sample_promotions


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
    assert narrative.file_summaries == [
        FileSummary(
            file="promotion_plan",
            issue_count=1,
            headline="1건의 이슈 — 대표: INVALID_PROMO_PRICE",
        )
    ]
    assert narrative.checklist == ["[INVALID_PROMO_PRICE] 행사가를 수정하세요."]


def test_merge_llm_file_summaries_keeps_server_counts() -> None:
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
        ),
        ValidationIssue(
            code="LOW_MARGIN_RATE",
            severity=Severity.WARNING,
            title="마진율이 낮습니다",
            message="마진율을 확인하세요.",
            entity={"promotion_id": "P-2", "product_code": "SKU-2"},
            location=IssueLocation(file="promotion_plan", row=3, column="promo_price"),
            observed="margin=1%",
            expected="margin>=5%",
            suggestion="행사가를 조정하세요.",
        ),
    ]
    fallback = build_fallback_narrative(issues)

    merged = merge_llm_file_summaries(
        [
            FileIssueGroup(
                file=item.file,
                issue_count=item.issue_count,
                representative=issues[0],
            )
            for item in fallback.file_summaries
        ],
        [],
    )

    assert merged[0].issue_count == 2


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
        file_summaries=[
            FileSummary(
                file="promotion_plan",
                issue_count=1,
                headline="1건의 이슈 — 대표: INVALID_PROMO_PRICE",
            )
        ],
        checklist=["[INVALID_PROMO_PRICE] 행사가를 수정하세요."],
        checklist_items=[],
        generated_by=GenerationSource.FALLBACK,
        created_at=datetime(2026, 7, 6, 14, 32, tzinfo=UTC),
        rule_set_version="test-version",
    )
    markdown = render_markdown_report(report)
    assert "# MD Preflight Report" in markdown
    assert "## Per-file Summary" in markdown
    assert "INVALID_PROMO_PRICE" in markdown
    assert "행사가를 수정하세요." in markdown
    assert "Rule Set Version: `test-version`" in markdown


def test_discount_rate_has_suggested_value() -> None:
    promotions = build_sample_promotions()
    ctx = build_context(
        promotions,
        build_sample_products(),
        build_sample_inventory(),
        RuleThresholds(),
    )
    issue = ValidationIssue(
        code="EXTREME_DISCOUNT_RATE",
        severity=Severity.WARNING,
        title="할인율이 너무 큽니다",
        message="설정된 최대 할인율을 초과했습니다.",
        entity={"promotion_id": "P-1", "product_code": "SKU-1"},
        location=IssueLocation(file="promotion_plan", row=2, column="promo_price"),
        observed="discount_rate=80.00%",
        expected="discount_rate < 70.00%",
        suggestion="할인율을 줄이거나 프로모션 구조를 다시 검토하세요.",
    )

    item = build_checklist_items(ctx, [issue])[0]

    assert item.suggested == "3001"


def test_non_mechanical_rules_have_null_suggested() -> None:
    ctx = build_context(
        build_sample_promotions(),
        build_sample_products(),
        build_sample_inventory(),
        RuleThresholds(),
    )
    issue = ValidationIssue(
        code="LOW_MARGIN_RATE",
        severity=Severity.WARNING,
        title="마진율이 기준보다 낮습니다",
        message="행사가 기준 마진율이 최소 기준을 충족하지 못했습니다.",
        entity={"promotion_id": "P-1", "product_code": "SKU-1"},
        location=IssueLocation(file="promotion_plan", row=2, column="promo_price"),
        observed="margin_rate=1.00%",
        expected="margin_rate >= 5.00%",
        suggestion="행사가를 조정하거나 원가를 재검토하세요.",
    )

    item = build_checklist_items(ctx, [issue])[0]

    assert item.suggested is None


def test_checklist_item_targets_issue_location() -> None:
    ctx = build_context(
        build_sample_promotions(),
        build_sample_products(),
        build_sample_inventory(),
        RuleThresholds(),
    )
    issue = ValidationIssue(
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

    item = build_checklist_items(ctx, [issue])[0]

    assert item.file == issue.location.file
    assert item.row == issue.location.row
    assert item.column == issue.location.column


def test_checklist_item_current_uses_source_cell_value() -> None:
    ctx = build_context(
        build_sample_promotions(),
        build_sample_products(),
        build_sample_inventory(),
        RuleThresholds(),
    )
    issue = ValidationIssue(
        code="INVALID_DATE_RANGE",
        severity=Severity.ERROR,
        title="종료일이 시작일보다 빠릅니다",
        message="기간을 확인하세요.",
        entity={"promotion_id": "P-2", "product_code": "SKU-2"},
        location=IssueLocation(file="promotion_plan", row=3, column="start_date"),
        observed="start=2026-07-15, end=2026-07-10",
        expected="start_date <= end_date",
        suggestion="시작일 또는 종료일을 수정하세요.",
    )

    item = build_checklist_items(ctx, [issue])[0]

    assert item.current == "2026-07-15"


def test_checklist_item_current_reads_product_master_value() -> None:
    ctx = build_context(
        build_sample_promotions(),
        build_sample_products(),
        build_sample_inventory(),
        RuleThresholds(),
    )
    issue = ValidationIssue(
        code="LOW_MARGIN_RATE",
        severity=Severity.WARNING,
        title="마진율이 기준보다 낮습니다",
        message="행사가 기준 마진율이 최소 기준을 충족하지 못했습니다.",
        entity={"promotion_id": "P-1", "product_code": "SKU-1"},
        location=IssueLocation(file="product_master", row=2, column="normal_price"),
        observed="margin_rate=1.00%",
        expected="margin_rate >= 5.00%",
        suggestion="정상가를 확인하세요.",
    )

    item = build_checklist_items(ctx, [issue])[0]

    assert item.current == "10000"


def test_checklist_item_current_returns_none_when_mapping_missing() -> None:
    ctx = build_context(
        build_sample_promotions(),
        build_sample_products(),
        build_sample_inventory(),
        RuleThresholds(),
    )
    issue = ValidationIssue(
        code="LOW_MARGIN_RATE",
        severity=Severity.WARNING,
        title="마진율이 기준보다 낮습니다",
        message="행사가 기준 마진율이 최소 기준을 충족하지 못했습니다.",
        entity={"promotion_id": "P-1", "product_code": "SKU-1"},
        location=IssueLocation(file="promotion_plan", row=999, column="promo_price"),
        observed="margin_rate=1.00%",
        expected="margin_rate >= 5.00%",
        suggestion="행사가를 조정하거나 원가를 재검토하세요.",
    )

    item = build_checklist_items(ctx, [issue])[0]

    assert item.current is None
