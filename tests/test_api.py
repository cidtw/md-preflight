from __future__ import annotations

import re
from collections.abc import Generator
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.domain.context import PreflightContext
from app.main import app, build_index_html
from app.schemas.history import HistoryBucket, RunHistoryRecord
from app.schemas.issue import Severity, ValidationIssue
from app.schemas.report import PreflightReport
from app.schemas.rule_meta import RuleMeta
from app.schemas.source_meta import SourceMeta
from app.services.clerk_auth import VerifiedClerkSession
from app.services.history_store import InMemoryHistoryStore
from tests.conftest import (
    build_sample_inventory,
    build_sample_products,
    build_sample_promotions,
)


def frame_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode()


def build_preflight_upload_files(
    promotions: pd.DataFrame | None = None,
    products: pd.DataFrame | None = None,
    inventory: pd.DataFrame | None = None,
) -> dict[str, tuple[str, bytes, str]]:
    return {
        "promotion_plan": (
            "promotion_plan.csv",
            frame_to_csv_bytes(promotions if promotions is not None else build_sample_promotions()),
            "text/csv",
        ),
        "product_master": (
            "product_master.csv",
            frame_to_csv_bytes(products if products is not None else build_sample_products()),
            "text/csv",
        ),
        "inventory": (
            "inventory.csv",
            frame_to_csv_bytes(inventory if inventory is not None else build_sample_inventory()),
            "text/csv",
        ),
    }


def test_validate_endpoint_when_uploading_sample_files() -> None:
    client = TestClient(app)

    response = client.post("/api/preflight/validate", files=build_preflight_upload_files())

    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert payload.generated_by == "fallback"
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
    assert payload.failed_rules == []
    assert payload.created_at.tzinfo is not None
    assert sum(item.issue_count for item in payload.file_summaries) == payload.summary.total_issues
    assert payload.rule_set_version
    assert payload.column_mappings == []

    stored = client.get(f"/api/preflight/runs/{payload.run_id}")

    assert stored.status_code == 200
    stored_payload = PreflightReport.model_validate(stored.json())
    assert stored_payload.run_id == payload.run_id


def test_validate_endpoint_accepts_korean_alias_headers(sample_files_dir: Path) -> None:
    """T51: alias_ko samples map headers and match dirty English sample issues."""
    client = TestClient(app)
    dirty_dir = sample_files_dir / "dirty"
    alias_dir = sample_files_dir / "alias_ko"

    def pack(base: Path) -> dict[str, tuple[str, bytes, str]]:
        return {
            "promotion_plan": (
                "promotion_plan.csv",
                (base / "promotion_plan.csv").read_bytes(),
                "text/csv",
            ),
            "product_master": (
                "product_master.csv",
                (base / "product_master.csv").read_bytes(),
                "text/csv",
            ),
            "inventory": (
                "inventory.csv",
                (base / "inventory.csv").read_bytes(),
                "text/csv",
            ),
        }

    dirty = PreflightReport.model_validate(
        client.post("/api/preflight/validate", files=pack(dirty_dir)).json()
    )
    response = client.post("/api/preflight/validate", files=pack(alias_dir))
    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())

    assert payload.summary.total_issues == dirty.summary.total_issues
    assert payload.summary.by_rule == dirty.summary.by_rule
    assert len(payload.column_mappings) >= 10
    originals = {item.original for item in payload.column_mappings}
    assert "상품코드" in originals or "SKU" in originals
    assert "행사가" in originals
    assert any(item.canonical == "promo_price" for item in payload.column_mappings)
    assert dirty.column_mappings == []

    md = client.get(f"/api/preflight/runs/{payload.run_id}/report.md")
    assert md.status_code == 200
    body = md.text
    assert "Column Mapping" in body
    assert "promo_price" in body


def test_preflight_without_auth_still_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    client = TestClient(app)

    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )

    assert response.status_code == 200


def test_preflight_without_auth_still_returns_200_when_history_store_init_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.deps._history_store_initialized", False)
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    monkeypatch.setattr(
        "app.api.deps.build_history_store",
        lambda: (_ for _ in ()).throw(RuntimeError("db boot failed")),
    )
    client = TestClient(app)

    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )

    assert response.status_code == 200


def test_preflight_with_auth_still_returns_200_when_history_store_init_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.deps._history_store_initialized", False)
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    monkeypatch.setattr(
        "app.api.deps.build_history_store",
        lambda: (_ for _ in ()).throw(RuntimeError("db boot failed")),
    )
    client = TestClient(app)

    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "user-123"},
        files=build_preflight_upload_files(),
    )

    assert response.status_code == 200


def test_history_endpoint_requires_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    client = TestClient(app)

    response = client.get("/api/preflight/history")

    assert response.status_code == 401


def test_history_endpoint_returns_buckets_for_signed_in_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    client = TestClient(app)

    create = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "user-123"},
        files=build_preflight_upload_files(),
    )

    assert create.status_code == 200
    response = client.get(
        "/api/preflight/history?granularity=day",
        headers={"x-md-preflight-user-id": "user-123"},
    )

    assert response.status_code == 200
    payload = TypeAdapter(list[HistoryBucket]).validate_python(response.json())
    assert len(payload) == 1
    assert payload[0].run_count == 1
    assert payload[0].error_total >= 0
    assert payload[0].warning_total >= 0
    assert payload[0].bucket.year >= 2000


def test_history_runs_endpoint_requires_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    client = TestClient(app)

    response = client.get("/api/preflight/history/runs")

    assert response.status_code == 401


def test_history_runs_endpoint_returns_latest_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    client = TestClient(app)

    first = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "user-123"},
        files=build_preflight_upload_files(),
    )
    second = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "user-123"},
        files=build_preflight_upload_files(),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    response = client.get(
        "/api/preflight/history/runs?limit=1",
        headers={"x-md-preflight-user-id": "user-123"},
    )

    assert response.status_code == 200
    payload = TypeAdapter(list[RunHistoryRecord]).validate_python(response.json())
    assert len(payload) == 1
    assert payload[0].run_id == PreflightReport.model_validate(second.json()).run_id


def test_history_endpoint_rejects_stub_header_when_clerk_mode_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publishable_key = "pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk"
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", publishable_key)
    from app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(
        "/api/preflight/history",
        headers={"x-md-preflight-user-id": "user-123"},
    )

    assert response.status_code == 401


def test_history_endpoint_accepts_verified_clerk_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def verify_token(
        *,
        token: str,
        publishable_key: str,
        authorized_parties: frozenset[str],
    ) -> VerifiedClerkSession:
        del token, publishable_key, authorized_parties
        return VerifiedClerkSession(user_id="user_clerk")

    publishable_key = "pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk"
    monkeypatch.setattr("app.api.deps.history_store_instance", InMemoryHistoryStore())
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", publishable_key)
    monkeypatch.setattr("app.api.deps.verify_clerk_session_token", verify_token)
    from app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    create = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"Authorization": "Bearer test-token"},
        files=build_preflight_upload_files(),
    )

    assert create.status_code == 200
    response = client.get(
        "/api/preflight/history?granularity=day",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = TypeAdapter(list[HistoryBucket]).validate_python(response.json())
    assert len(payload) == 1
    assert payload[0].run_count == 1


def test_preflight_history_append_failure_does_not_break_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenHistoryStore:
        def append(self, record: RunHistoryRecord) -> None:
            del record
            raise RuntimeError("append broke")

        def query(self, user_id: str, granularity: str) -> list[HistoryBucket]:
            del user_id, granularity
            return []

        def list_runs(self, user_id: str, *, limit: int) -> list[RunHistoryRecord]:
            del user_id, limit
            return []

    monkeypatch.setattr("app.api.deps.history_store_instance", BrokenHistoryStore())
    client = TestClient(app)

    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        headers={"x-md-preflight-user-id": "user-123"},
        files=build_preflight_upload_files(),
    )

    assert response.status_code == 200


def test_index_html_injects_clerk_publishable_key() -> None:
    from app.core.config import Settings

    html = build_index_html(Settings.model_construct(clerk_publishable_key="pk_test_value"))

    assert "window.__MDP_CONFIG__" in html
    assert "pk_test_value" in html


def test_index_html_injects_upload_limits_matching_server_settings() -> None:
    from app.core.config import Settings

    settings = Settings.model_construct(
        clerk_publishable_key=None,
        max_upload_bytes=1234,
        allowed_extensions=(".csv", ".xlsx", ".tsv"),
    )
    html = build_index_html(settings)

    assert '"maxUploadBytes": 1234' in html
    assert '".csv", ".xlsx", ".tsv"' in html


def test_index_html_injects_auth_mode() -> None:
    from app.core.config import Settings

    off_settings = Settings.model_construct(
        clerk_publishable_key=None,
        clerk_secret_key=None,
        allow_stub_auth=False,
    )
    stub_settings = Settings.model_construct(
        clerk_publishable_key=None,
        clerk_secret_key=None,
        allow_stub_auth=True,
    )

    assert '"authMode": "off"' in build_index_html(off_settings)
    assert '"authMode": "stub"' in build_index_html(stub_settings)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health_reports_auth_mode_and_backends_without_secrets() -> None:
    client = TestClient(app)

    response = client.get("/api/preflight/health")

    assert response.status_code == 200
    payload = TypeAdapter(dict[str, str]).validate_python(response.json())
    assert payload["status"] == "ok"
    assert payload["auth_mode"] in {"clerk", "stub", "off"}
    assert payload["run_backend"] in {"postgres", "in_memory"}
    assert payload["history_backend"] in {"postgres", "in_memory"}
    assert "secret" not in str(payload).lower()
    assert "key" not in str(payload).lower()


def test_rules_endpoint_returns_registry() -> None:
    client = TestClient(app)

    response = client.get("/api/preflight/rules")

    assert response.status_code == 200
    rules = TypeAdapter(list[RuleMeta]).validate_python(response.json())
    assert [rule.code for rule in rules] == [
        "INVALID_DATE_RANGE",
        "MISSING_PRODUCT_MASTER",
        "INCOMPLETE_PRODUCT_MASTER",
        "INVALID_PROMO_PRICE",
        "EXTREME_DISCOUNT_RATE",
        "LOW_MARGIN_RATE",
        "DUPLICATE_MASTER_CODE",
        "INVENTORY_SHORTAGE_RISK",
        "INBOUND_DATE_CONFLICT",
        "MISSING_BENEFIT_CONDITION",
    ]


def test_sources_catalog_lists_upload_available() -> None:
    client = TestClient(app)

    response = client.get("/api/preflight/sources")

    assert response.status_code == 200
    payload = TypeAdapter(list[SourceMeta]).validate_python(response.json())
    statuses = {item.id: item.status for item in payload}
    assert statuses["upload"] == "available"
    assert statuses["notion"] == "planned"
    assert statuses["google_sheets"] == "planned"
    assert statuses["csv_url"] == "planned"


def test_validate_endpoint_reports_failed_rules_when_a_rule_raises(
    sample_files_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)

    class BrokenRuleError(Exception):
        pass

    class BrokenRule:
        code: str = "BROKEN_RULE"
        severity: Severity = Severity.WARNING
        description: str = "broken"

        def apply(self, _ctx: PreflightContext) -> list[ValidationIssue]:
            raise BrokenRuleError

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


@pytest.mark.parametrize(
    ("duplicate_source", "products", "inventory"),
    [
        (
            "product_master",
            build_sample_products().iloc[[0, 0]].reset_index(drop=True),
            build_sample_inventory().iloc[[0]].reset_index(drop=True),
        ),
        (
            "inventory",
            build_sample_products().iloc[[0, 1]].reset_index(drop=True),
            build_sample_inventory().iloc[[0, 0]].reset_index(drop=True),
        ),
    ],
)
def test_validate_endpoint_duplicate_master_codes_return_warning_instead_of_422(
    duplicate_source: str,
    products: pd.DataFrame,
    inventory: pd.DataFrame,
) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/preflight/validate",
        files=build_preflight_upload_files(products=products, inventory=inventory),
    )

    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    duplicate_issues = [issue for issue in payload.issues if issue.code == "DUPLICATE_MASTER_CODE"]
    assert payload.summary.by_rule["DUPLICATE_MASTER_CODE"] == 1
    assert len(duplicate_issues) == 1
    assert duplicate_issues[0].severity == Severity.WARNING
    assert duplicate_issues[0].location.file == duplicate_source


def test_validate_endpoint_unique_master_codes_do_not_add_duplicate_warning() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/preflight/validate",
        files=build_preflight_upload_files(
            products=build_sample_products().iloc[[0]].reset_index(drop=True),
            inventory=build_sample_inventory().iloc[[0]].reset_index(drop=True),
        ),
    )

    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert "DUPLICATE_MASTER_CODE" not in payload.summary.by_rule
    assert all(issue.code != "DUPLICATE_MASTER_CODE" for issue in payload.issues)


def test_post_preflight_missing_column_returns_422() -> None:
    client = TestClient(app)
    promotions = build_sample_promotions().drop(columns=["benefit_condition"])

    response = client.post(
        "/api/preflight",
        data={"use_llm": "true"},
        files=build_preflight_upload_files(promotions=promotions),
    )

    assert response.status_code == 422


def test_post_preflight_saved_run_is_retrievable() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/preflight",
        data={"use_llm": "true"},
        files=build_preflight_upload_files(),
    )

    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    stored = client.get(f"/api/preflight/runs/{payload.run_id}")

    assert stored.status_code == 200
    stored_payload = PreflightReport.model_validate(stored.json())
    assert stored_payload == payload


def test_report_has_created_at() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )

    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert payload.created_at.tzinfo is not None


def test_report_md_download() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/preflight",
        data={"use_llm": "true"},
        files=build_preflight_upload_files(),
    )

    assert create_response.status_code == 200
    payload = PreflightReport.model_validate(create_response.json())
    response = client.get(f"/api/preflight/runs/{payload.run_id}/report.md")

    assert response.status_code == 200
    assert "markdown" in response.headers["content-type"]
    assert "Created At (UTC):" in response.text
    assert "# MD Preflight Report" in response.text
    assert "## Per-file Summary" in response.text
    assert "## Issues" in response.text


def test_download_filename_is_timestamped() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )

    assert create_response.status_code == 200
    payload = PreflightReport.model_validate(create_response.json())
    response = client.get(f"/api/preflight/runs/{payload.run_id}/report.md")

    assert response.status_code == 200
    assert re.search(
        r'preflight-\d{4}-\d{2}-\d{2}-\d{4}-report\.md',
        response.headers["content-disposition"],
    ) is not None


def test_report_md_unknown_run_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/preflight/runs/unknown-run/report.md")

    assert response.status_code == 404


def test_preflight_use_llm_false_is_fallback() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )
    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert payload.generated_by == "fallback"


def test_preflight_llm_success_sets_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.schemas.report import GenerationSource
    from app.services.llm_service import Narrative

    class StubGenerator:
        def generate(self, summary: object, issues: object) -> Narrative:
            _ = (summary, issues)
            return Narrative(
                ai_summary="요약 완료",
                file_summaries=[],
                checklist=["- 항목 1"],
                source=GenerationSource.LLM,
            )

    def mock_success_gen(settings: object, use_llm: bool) -> StubGenerator:
        _ = (settings, use_llm)
        return StubGenerator()

    monkeypatch.setattr(
        "app.api.routes.get_narrative_generator",
        mock_success_gen,
    )

    client = TestClient(app)
    response = client.post(
        "/api/preflight",
        data={"use_llm": "true"},
        files=build_preflight_upload_files(),
    )
    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert payload.generated_by == "llm"
    assert payload.summary.total_issues == 9


def test_preflight_llm_error_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    from typing import final

    import httpx
    from anthropic import APIError

    @final
    class StubMessagesWithError:
        def parse(self, **kwargs: object) -> object:
            _ = kwargs
            dummy_request = httpx.Request("POST", "https://api.anthropic.com")
            raise APIError("API Error", request=dummy_request, body=None)

    @final
    class StubAnthropicWithError:
        def __init__(self) -> None:
            self.messages = StubMessagesWithError()

    from typing import cast

    from anthropic import Anthropic

    from app.services.llm_service import (
        FallbackNarrativeGenerator,
        FallbackOnErrorNarrativeGenerator,
        LLMNarrativeGenerator,
    )

    def mock_get_narrative_generator(settings: object, use_llm: bool) -> object:
        _ = (settings, use_llm)
        stub_client = StubAnthropicWithError()
        client_as_anthropic = cast(Anthropic, cast(object, stub_client))
        return FallbackOnErrorNarrativeGenerator(
            primary=LLMNarrativeGenerator(client=client_as_anthropic, model="claude-test"),
            fallback=FallbackNarrativeGenerator(),
        )

    monkeypatch.setattr(
        "app.api.routes.get_narrative_generator",
        mock_get_narrative_generator,
    )

    client = TestClient(app)
    response = client.post(
        "/api/preflight",
        data={"use_llm": "true"},
        files=build_preflight_upload_files(),
    )
    assert response.status_code == 200
    payload = PreflightReport.model_validate(response.json())
    assert payload.generated_by == "fallback"
    assert payload.summary.total_issues == 9


def test_rejects_bad_extension_400() -> None:
    client = TestClient(app)
    files = build_preflight_upload_files()
    files["promotion_plan"] = ("promotion_plan.txt", files["promotion_plan"][1], "text/plain")
    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=files,
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_rejects_oversized_file_413(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.deps import get_app_settings
    from app.core.config import Settings

    custom_settings = Settings(max_upload_bytes=10)
    monkeypatch.setitem(app.dependency_overrides, get_app_settings, lambda: custom_settings)

    client = TestClient(app)
    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )
    assert response.status_code == 413
    assert "exceeds size limit" in response.json()["detail"]


def test_valid_upload_still_200() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(),
    )
    assert response.status_code == 200


def test_missing_column_still_422() -> None:
    client = TestClient(app)
    promotions = build_sample_promotions().drop(columns=["benefit_type"])
    response = client.post(
        "/api/preflight",
        data={"use_llm": "false"},
        files=build_preflight_upload_files(promotions=promotions),
    )
    assert response.status_code == 422


def test_settings_loads_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")

    settings = Settings()
    assert settings.openai_api_key == "test-openai-key"
    assert settings.anthropic_api_key == "test-anthropic-key"
