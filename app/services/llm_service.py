from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import ClassVar, Final, Protocol

from anthropic import Anthropic, AnthropicError
from pydantic import BaseModel, ConfigDict
from typing_extensions import override

from app.schemas.issue import ValidationIssue
from app.schemas.report import GenerationSource, PreflightSummary

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT: Final = (
    "너는 판정을 수정하거나 에러를 정당화할 권한이 없다. "
    "아래 검수 결과를 재판단하지 말고 "
    "담당자용 한국어 요약(3~5문장)과 우선순위 체크리스트로만 변환하라. "
    "새 이슈를 만들지 마라. 발견되지 않은 룰 코드를 언급하지 마라."
)


@dataclass(frozen=True, slots=True)
class Narrative:
    ai_summary: str
    checklist: list[str]
    source: GenerationSource


FallbackNarrative = Narrative


class NarrativeGenerator(Protocol):
    def generate(
        self,
        summary: PreflightSummary,
        issues: list[ValidationIssue],
    ) -> Narrative: ...


@dataclass(frozen=True, slots=True)
class LLMNarrativeParseError(Exception):
    model: str

    @override
    def __str__(self) -> str:
        return f"failed to parse narrative response for model {self.model}"


class LLMNarrative(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    ai_summary: str
    checklist: list[str]


@dataclass(frozen=True, slots=True)
class FallbackNarrativeGenerator:
    def generate(self, summary: PreflightSummary, issues: list[ValidationIssue]) -> Narrative:
        if summary.total_issues == 0 and not issues:
            return build_fallback_narrative(issues)
        narrative = build_fallback_narrative(issues)
        return Narrative(
            ai_summary=narrative.ai_summary,
            checklist=narrative.checklist,
            source=GenerationSource.FALLBACK,
        )


@dataclass(frozen=True, slots=True)
class LLMNarrativeGenerator:
    client: Anthropic
    model: str

    def generate(self, summary: PreflightSummary, issues: list[ValidationIssue]) -> Narrative:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=2000,
            thinking={"type": "disabled"},
            output_format=LLMNarrative,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "summary": summary.model_dump(mode="json"),
                            "issues": [
                                {
                                    "code": issue.code,
                                    "severity": issue.severity.value,
                                    "title": issue.title,
                                    "observed": issue.observed,
                                    "expected": issue.expected,
                                    "suggestion": issue.suggestion,
                                }
                                for issue in issues
                            ],
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
        )

        parsed = response.parsed_output
        if parsed is None:
            raise LLMNarrativeParseError(model=self.model)

        return Narrative(
            ai_summary=parsed.ai_summary,
            checklist=parsed.checklist,
            source=GenerationSource.LLM,
        )


@dataclass(frozen=True, slots=True)
class FallbackOnErrorNarrativeGenerator:
    primary: NarrativeGenerator
    fallback: FallbackNarrativeGenerator

    def generate(self, summary: PreflightSummary, issues: list[ValidationIssue]) -> Narrative:
        try:
            return self.primary.generate(summary, issues)
        except (AnthropicError, LLMNarrativeParseError) as exc:
            logger.warning("llm narrative generation failed; using fallback: %s", exc)
            return self.fallback.generate(summary, issues)


def build_fallback_narrative(issues: list[ValidationIssue]) -> FallbackNarrative:
    if not issues:
        return FallbackNarrative(
            ai_summary="검수 결과 이상 없음. 모든 파일이 규칙을 통과했습니다.",
            checklist=["검수 결과를 검토하고 다음 프로모션 등록 단계로 진행하세요."],
            source=GenerationSource.FALLBACK,
        )
    first_issue = issues[0]
    return FallbackNarrative(
        ai_summary=(
            f"총 {len(issues)}건의 이슈가 발견되었습니다. "
            f"가장 먼저 확인할 항목은 {first_issue.code}입니다."
        ),
        checklist=[
            f"[{issue.code}] {issue.suggestion or issue.title}" for issue in issues
        ],
        source=GenerationSource.FALLBACK,
    )
