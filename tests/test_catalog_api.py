from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.catalog import PreflightCatalog


def test_catalog_endpoint_exposes_thresholds_aliases_and_rules() -> None:
    client = TestClient(app)

    response = client.get("/api/preflight/catalog")

    assert response.status_code == 200
    catalog = PreflightCatalog.model_validate(response.json())
    assert catalog.thresholds.max_discount_rate == 0.7
    assert catalog.thresholds.min_margin_rate == 0.05
    assert len(catalog.rules) == 10
    assert len(catalog.sources) == 3
    source_ids = {item.source for item in catalog.sources}
    assert source_ids == {"promotion_plan", "product_master", "inventory"}
    promo = next(item for item in catalog.sources if item.source == "promotion_plan")
    product_code = next(col for col in promo.columns if col.canonical == "product_code")
    assert "상품코드" in product_code.aliases or "sku" in {
        a.lower() for a in product_code.aliases
    }
    assert ".csv" in catalog.allowed_extensions or catalog.allowed_extensions
