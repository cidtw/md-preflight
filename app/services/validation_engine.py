from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

from fastapi import UploadFile

from app.core.errors import IngestError
from app.core.rule_config import RuleThresholds
from app.domain.context import PreflightContext
from app.ingest.loader import load_table
from app.ingest.normalize import build_context
from app.rules import RULES
from app.rules.base import Rule
from app.schemas.issue import ValidationIssue
from app.schemas.report import GenerationSource, PreflightReport, PreflightSummary

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UploadedFiles:
    promotion_plan: UploadFile
    product_master: UploadFile
    inventory: UploadFile


async def read_upload(file: UploadFile) -> tuple[str, bytes]:
    content = await file.read()
    if not content:
        msg = f"Empty upload: {file.filename}"
        raise IngestError(msg)
    return file.filename or "", content


async def build_uploaded_context(
    files: UploadedFiles,
    thresholds: RuleThresholds,
) -> PreflightContext:
    promotion_name, promotion_content = await read_upload(files.promotion_plan)
    product_name, product_content = await read_upload(files.product_master)
    inventory_name, inventory_content = await read_upload(files.inventory)
    return build_context(
        load_table(promotion_name, promotion_content),
        load_table(product_name, product_content),
        load_table(inventory_name, inventory_content),
        thresholds,
    )


def validate_context(
    ctx: PreflightContext,
    *,
    rules: Sequence[Rule] | None = None,
) -> PreflightReport:
    issues: list[ValidationIssue] = []
    failed_rules: list[str] = []
    active_rules = RULES if rules is None else rules
    for rule in active_rules:
        try:
            issues.extend(rule.apply(ctx))
        except Exception:
            logger.exception("rule execution failed: %s", rule.code)
            failed_rules.append(rule.code)
    summary = build_summary(issues, checked_rows=len(ctx.promotions))
    return PreflightReport(
        run_id=uuid4().hex,
        summary=summary,
        issues=issues,
        ai_summary=deterministic_ai_summary(issues),
        checklist=deterministic_checklist(issues),
        generated_by=GenerationSource.FALLBACK,
        failed_rules=failed_rules,
    )


def build_summary(issues: list[ValidationIssue], checked_rows: int) -> PreflightSummary:
    by_severity = Counter(issue.severity.value for issue in issues)
    by_rule = Counter(issue.code for issue in issues)
    total_issues = len(issues)
    return PreflightSummary(
        total_issues=total_issues,
        by_severity={
            "error": by_severity.get("error", 0),
            "warning": by_severity.get("warning", 0),
            "info": by_severity.get("info", 0),
        },
        by_rule=dict(by_rule),
        passed=by_severity.get("error", 0) == 0,
        checked_rows=checked_rows,
    )


def deterministic_ai_summary(issues: list[ValidationIssue]) -> str:
    if not issues:
        return "검수 결과 이상 없음. 모든 파일이 규칙을 통과했습니다."
    first_issue = issues[0]
    return (
        f"총 {len(issues)}건의 이슈가 발견되었습니다. "
        f"가장 먼저 확인할 항목은 {first_issue.code}입니다."
    )


def deterministic_checklist(issues: list[ValidationIssue]) -> list[str]:
    return [
        f"[{issue.code}] {issue.suggestion or issue.title}"
        for issue in issues
    ]
