from app.schemas.issue import IssueLocation, Severity, ValidationIssue


def test_related_locations_optional_backward_compat() -> None:
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

    assert issue.related_locations == []
