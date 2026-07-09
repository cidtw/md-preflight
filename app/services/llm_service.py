from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import ClassVar, Final, Protocol

from anthropic import Anthropic, AnthropicError
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ConfigDict
from typing_extensions import override

from app.schemas.issue import ValidationIssue
from app.schemas.report import FileSummary, GenerationSource, PreflightSummary

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
    file_summaries: list[FileSummary]
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
class NarrativeGenerationError(Exception):
    provider: str
    model: str
    reason: str

    @override
    def __str__(self) -> str:
        return f"{self.provider} narrative generation failed for model {self.model}: {self.reason}"


@dataclass(frozen=True, slots=True)
class LLMNarrativeParseError(NarrativeGenerationError):
    provider: str
    model: str
    reason: str = "response could not be parsed"

    @override
    def __str__(self) -> str:
        return (
            f"failed to parse narrative response for provider {self.provider}, "
            f"model {self.model}"
        )


class LLMNarrative(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    ai_summary: str
    file_summaries: list[LLMFileSummary]
    checklist: list[str]


class LLMFileSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    file: str
    headline: str


@dataclass(frozen=True, slots=True)
class FileIssueGroup:
    file: str
    issue_count: int
    representative: ValidationIssue


@dataclass(frozen=True, slots=True)
class FallbackNarrativeGenerator:
    def generate(self, summary: PreflightSummary, issues: list[ValidationIssue]) -> Narrative:
        if summary.total_issues == 0 and not issues:
            return build_fallback_narrative(issues)
        narrative = build_fallback_narrative(issues)
        return Narrative(
            ai_summary=narrative.ai_summary,
            file_summaries=narrative.file_summaries,
            checklist=narrative.checklist,
            source=GenerationSource.FALLBACK,
        )


@dataclass(frozen=True, slots=True)
class LLMNarrativeGenerator:
    client: Anthropic
    model: str

    def generate(self, summary: PreflightSummary, issues: list[ValidationIssue]) -> Narrative:
        groups = group_by_file(issues)
        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=2000,
                thinking={"type": "disabled"},
                output_format=LLMNarrative,
                system=_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": build_llm_payload(summary, issues, groups),
                    }
                ],
            )
        except AnthropicError as exc:
            raise NarrativeGenerationError(
                provider="anthropic",
                model=self.model,
                reason=str(exc),
            ) from exc

        parsed = response.parsed_output
        if parsed is None:
            raise LLMNarrativeParseError(provider="anthropic", model=self.model)

        return build_narrative_from_parsed(groups, parsed)


@dataclass(frozen=True, slots=True)
class OpenAINarrativeGenerator:
    client: OpenAI
    model: str

    def generate(self, summary: PreflightSummary, issues: list[ValidationIssue]) -> Narrative:
        groups = group_by_file(issues)
        try:
            response = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": build_llm_payload(summary, issues, groups)},
                ],
                response_format=LLMNarrative,
            )
        except OpenAIError as exc:
            raise NarrativeGenerationError(
                provider="openai",
                model=self.model,
                reason=str(exc),
            ) from exc

        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise LLMNarrativeParseError(provider="openai", model=self.model)

        return build_narrative_from_parsed(groups, parsed)


def build_narrative_from_parsed(
    groups: list[FileIssueGroup],
    parsed: LLMNarrative,
) -> Narrative:
    return Narrative(
        ai_summary=parsed.ai_summary,
        file_summaries=merge_llm_file_summaries(groups, parsed.file_summaries),
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
        except NarrativeGenerationError as exc:
            logger.warning("llm narrative generation failed; using fallback: %s", exc)
            return self.fallback.generate(summary, issues)


def build_llm_payload(
    summary: PreflightSummary,
    issues: list[ValidationIssue],
    groups: list[FileIssueGroup],
) -> str:
    return json.dumps(
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
            "file_groups": [
                {
                    "file": group.file,
                    "issue_count": group.issue_count,
                    "representative_code": group.representative.code,
                    "representative_title": group.representative.title,
                    "representative_severity": group.representative.severity.value,
                }
                for group in groups
            ],
        },
        ensure_ascii=False,
    )


def build_fallback_narrative(issues: list[ValidationIssue]) -> FallbackNarrative:
    if not issues:
        return FallbackNarrative(
            ai_summary="검수 결과 이상 없음. 모든 파일이 규칙을 통과했습니다.",
            file_summaries=[],
            checklist=["검수 결과를 검토하고 다음 프로모션 등록 단계로 진행하세요."],
            source=GenerationSource.FALLBACK,
        )
    first_issue = issues[0]
    groups = group_by_file(issues)
    return FallbackNarrative(
        ai_summary=(
            f"총 {len(issues)}건의 이슈가 발견되었습니다. "
            f"가장 먼저 확인할 항목은 {first_issue.code}입니다."
        ),
        file_summaries=[
            FileSummary(
                file=group.file,
                issue_count=group.issue_count,
                headline=f"{group.issue_count}건의 이슈 — 대표: {group.representative.code}",
            )
            for group in groups
        ],
        checklist=[
            f"[{issue.code}] {issue.suggestion or issue.title}" for issue in issues
        ],
        source=GenerationSource.FALLBACK,
    )


def group_by_file(issues: list[ValidationIssue]) -> list[FileIssueGroup]:
    grouped: dict[str, list[ValidationIssue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.location.file].append(issue)

    return [
        FileIssueGroup(
            file=file,
            issue_count=len(file_issues),
            representative=sorted(
                file_issues,
                key=lambda candidate: (
                    severity_rank(candidate.severity.value),
                    candidate.code,
                ),
            )[0],
        )
        for file, file_issues in sorted(grouped.items())
    ]


def merge_llm_file_summaries(
    groups: list[FileIssueGroup],
    llm_summaries: list[LLMFileSummary],
) -> list[FileSummary]:
    headlines = {summary.file: summary.headline for summary in llm_summaries}
    return [
        FileSummary(
            file=group.file,
            issue_count=group.issue_count,
            headline=headlines.get(
                group.file,
                f"{group.issue_count}건의 이슈 — 대표: {group.representative.code}",
            ),
        )
        for group in groups
    ]


def severity_rank(severity: str) -> int:
    return {"error": 0, "warning": 1, "info": 2}.get(severity, 3)
