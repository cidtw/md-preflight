from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import UploadFile

from app.core.errors import IngestError
from app.core.rule_config import RuleThresholds
from app.domain.context import PreflightContext
from app.ingest.loader import load_table
from app.ingest.normalize import build_context
from app.rules import RULES, compute_rule_set_version
from app.rules.base import Rule
from app.schemas.issue import ValidationIssue
from app.schemas.report import PreflightReport, PreflightSummary
from app.services.checklist_service import build_checklist_items
from app.services.llm_service import FallbackNarrativeGenerator, NarrativeGenerator

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
    generator: NarrativeGenerator | None = None,
) -> PreflightReport:
    issues: list[ValidationIssue] = []
    failed_rules: list[str] = []
    active_rules = RULES if rules is None else rules
    narrative_generator = FallbackNarrativeGenerator() if generator is None else generator
    for rule in active_rules:
        try:
            issues.extend(rule.apply(ctx))
        except Exception:
            # Isolate per-rule failures so one broken rule cannot fail the whole run.
            logger.exception("rule execution failed: %s", rule.code)
            failed_rules.append(rule.code)
    summary = build_summary(issues, checked_rows=len(ctx.promotions))
    narrative = narrative_generator.generate(summary, issues)
    checklist_items = build_checklist_items(ctx, issues)
    return PreflightReport(
        run_id=uuid4().hex,
        summary=summary,
        issues=issues,
        ai_summary=narrative.ai_summary,
        file_summaries=narrative.file_summaries,
        checklist=narrative.checklist,
        checklist_items=checklist_items,
        generated_by=narrative.source,
        failed_rules=failed_rules,
        created_at=datetime.now(tz=UTC),
        rule_set_version=compute_rule_set_version(ctx.thresholds, rules=active_rules),
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
