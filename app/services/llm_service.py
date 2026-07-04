from __future__ import annotations

from dataclasses import dataclass

from app.schemas.issue import ValidationIssue


@dataclass(frozen=True, slots=True)
class FallbackNarrative:
    ai_summary: str
    checklist: list[str]


def build_fallback_narrative(issues: list[ValidationIssue]) -> FallbackNarrative:
    if not issues:
        return FallbackNarrative(
            ai_summary="검수 결과 이상 없음. 모든 파일이 규칙을 통과했습니다.",
            checklist=["검수 결과를 검토하고 다음 프로모션 등록 단계로 진행하세요."],
        )
    first_issue = issues[0]
    return FallbackNarrative(
        ai_summary=(
            f"총 {len(issues)}건의 이슈가 발견되었습니다. "
            f"가장 먼저 확인할 항목은 {first_issue.code}입니다."
        ),
        checklist=[
            f"[{issue.code}] {issue.suggestion or issue.title}"
            for issue in issues
        ],
    )
