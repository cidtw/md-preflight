from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pytest
from anthropic import Anthropic, APIConnectionError, APIError, RateLimitError
from httpx import Request, Response
from pydantic import BaseModel, TypeAdapter
from typing_extensions import TypedDict

from app.schemas.issue import IssueLocation, Severity, ValidationIssue
from app.schemas.report import FileSummary, GenerationSource, PreflightSummary
from app.services.llm_service import LLMNarrativeGenerator, Narrative


class _IssuePayload(TypedDict):
    code: str
    severity: str
    title: str
    observed: str | None
    expected: str | None
    suggestion: str | None


class _SummaryPayload(TypedDict):
    total_issues: int
    by_severity: dict[str, int]
    by_rule: dict[str, int]
    passed: bool
    checked_rows: int


class _PromptPayload(TypedDict):
    summary: _SummaryPayload
    issues: list[_IssuePayload]
    file_groups: list[dict[str, str | int]]


class _MessagePayload(TypedDict):
    role: str
    content: str


class _ThinkingPayload(TypedDict):
    type: str


_PROMPT_PAYLOAD_ADAPTER: Final[TypeAdapter[_PromptPayload]] = TypeAdapter(_PromptPayload)
_MESSAGE_PAYLOAD_LIST_ADAPTER: Final[TypeAdapter[list[_MessagePayload]]] = TypeAdapter(
    list[_MessagePayload]
)


@dataclass(frozen=True, slots=True)
class _ParsedFileSummaryStub:
    file: str
    headline: str


@dataclass(frozen=True, slots=True)
class _ParsedNarrativeStub:
    ai_summary: str
    file_summaries: list[_ParsedFileSummaryStub]
    checklist: list[str]


@dataclass(frozen=True, slots=True)
class _ParseCall:
    model: str
    max_tokens: int
    thinking: _ThinkingPayload
    output_format: type[BaseModel]
    system: str
    messages: list[_MessagePayload]


@dataclass(frozen=True, slots=True)
class _ParseResponse:
    parsed_output: _ParsedNarrativeStub | None


class _ParseRecorder:
    _parsed_output: _ParsedNarrativeStub | None
    _error: Exception | None
    last_call: _ParseCall | None

    def __init__(
        self,
        *,
        parsed_output: _ParsedNarrativeStub | None = None,
        error: Exception | None = None,
    ) -> None:
        self._parsed_output = parsed_output
        self._error = error
        self.last_call = None

    def __call__(
        self,
        *,
        model: str,
        max_tokens: int,
        thinking: _ThinkingPayload,
        output_format: type[BaseModel],
        system: str,
        messages: list[_MessagePayload],
    ) -> _ParseResponse:
        self.last_call = _ParseCall(
            model=model,
            max_tokens=max_tokens,
            thinking=thinking,
            output_format=output_format,
            system=system,
            messages=messages,
        )
        if self._error is not None:
            raise self._error
        return _ParseResponse(parsed_output=self._parsed_output)


def _build_llm_client(
    monkeypatch: pytest.MonkeyPatch,
    parse_recorder: _ParseRecorder,
) -> Anthropic:
    client = Anthropic(api_key="test")
    monkeypatch.setattr(client.messages, "parse", parse_recorder)
    return client


def _make_summary() -> PreflightSummary:
    return PreflightSummary(
        total_issues=1,
        by_severity={"error": 1, "warning": 0, "info": 0},
        by_rule={"INVALID_PROMO_PRICE": 1},
        passed=False,
        checked_rows=6,
    )


def _make_issue() -> ValidationIssue:
    return ValidationIssue(
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


def _make_sensitive_issue() -> ValidationIssue:
    return ValidationIssue(
        code="INVALID_PROMO_PRICE",
        severity=Severity.ERROR,
        title="행사가가 유효하지 않습니다",
        message="프로모션 가격을 확인하세요.",
        entity={
            "promotion_id": "PROMO-SECRET",
            "product_name": "Ultra Secret Widget",
            "location": "Gangnam",
            "normal_price": "19900",
            "cost": "12000",
        },
        location=IssueLocation(file="raw_prices", row=88, column="promo_price"),
        observed="promo_price=21000",
        expected="0 < promo_price <= normal_price",
        suggestion="행사가를 수정하세요.",
    )


def test_llm_generator_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    parse = _ParseRecorder(
        parsed_output=_ParsedNarrativeStub(
            ai_summary="총 1건의 이슈가 발견되었습니다.",
            file_summaries=[
                _ParsedFileSummaryStub(
                    file="promotion_plan",
                    headline="가격 점검이 필요합니다.",
                )
            ],
            checklist=["[INVALID_PROMO_PRICE] 행사가를 수정하세요."],
        )
    )
    generator = LLMNarrativeGenerator(
        client=_build_llm_client(monkeypatch, parse),
        model="claude-test-model",
    )

    narrative = generator.generate(_make_summary(), [_make_issue()])

    assert narrative == Narrative(
        ai_summary="총 1건의 이슈가 발견되었습니다.",
        file_summaries=[
            FileSummary(
                file="promotion_plan",
                issue_count=1,
                headline="가격 점검이 필요합니다.",
            )
        ],
        checklist=["[INVALID_PROMO_PRICE] 행사가를 수정하세요."],
        source=GenerationSource.LLM,
    )
    assert parse.last_call is not None


def test_llm_generator_prompt_uses_only_allowed_payload_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parse = _ParseRecorder(
        parsed_output=_ParsedNarrativeStub(
            ai_summary="요약",
            file_summaries=[
                _ParsedFileSummaryStub(
                    file="raw_prices",
                    headline="가격을 검토하세요.",
                )
            ],
            checklist=["체크리스트"],
        )
    )
    generator = LLMNarrativeGenerator(
        client=_build_llm_client(monkeypatch, parse),
        model="claude-test-model",
    )

    _ = generator.generate(_make_summary(), [_make_sensitive_issue()])

    assert parse.last_call is not None
    assert parse.last_call.thinking == {"type": "disabled"}
    assert getattr(parse.last_call.output_format, "__name__", "") == "LLMNarrative"
    payload = _PROMPT_PAYLOAD_ADAPTER.validate_json(
        _MESSAGE_PAYLOAD_LIST_ADAPTER.validate_python(parse.last_call.messages)[0]["content"]
    )
    assert "새 이슈를 만들지 마라" in parse.last_call.system
    assert payload["summary"] == _make_summary().model_dump(mode="json")
    assert payload["issues"] == [
        {
            "code": "INVALID_PROMO_PRICE",
            "severity": "error",
            "title": "행사가가 유효하지 않습니다",
            "observed": "promo_price=21000",
            "expected": "0 < promo_price <= normal_price",
            "suggestion": "행사가를 수정하세요.",
        }
    ]


@pytest.mark.parametrize(
    ("sdk_error"),
    [
        APIError(
            "anthropic api error",
            request=Request("POST", "https://api.anthropic.com/v1/messages"),
            body=None,
        ),
        APIConnectionError(
            message="connection error",
            request=Request("POST", "https://api.anthropic.com/v1/messages"),
        ),
        RateLimitError(
            "rate limit",
            response=Response(
                429,
                request=Request("POST", "https://api.anthropic.com/v1/messages"),
            ),
            body=None,
        ),
    ],
)
def test_llm_generator_raises_on_sdk_errors(
    monkeypatch: pytest.MonkeyPatch,
    sdk_error: Exception,
) -> None:
    generator = LLMNarrativeGenerator(
        client=_build_llm_client(monkeypatch, _ParseRecorder(error=sdk_error)),
        model="claude-test-model",
    )

    with pytest.raises(type(sdk_error)):
        _ = generator.generate(_make_summary(), [_make_issue()])
