from __future__ import annotations

import math
from collections.abc import Callable
from typing import TypeAlias

import pandas as pd

from app.domain.columns import SourceFile
from app.domain.context import PreflightContext
from app.schemas.issue import ValidationIssue
from app.schemas.report import ChecklistItem

ChecklistSuggester: TypeAlias = Callable[[PreflightContext, ValidationIssue], str | None]


def build_checklist_items(
    ctx: PreflightContext,
    issues: list[ValidationIssue],
) -> list[ChecklistItem]:
    return [
        ChecklistItem(
            code=issue.code,
            file=issue.location.file,
            row=issue.location.row,
            column=issue.location.column,
            current=lookup_current_value(ctx, issue),
            suggested=suggest_value(ctx, issue),
            rationale=issue.suggestion or issue.title,
        )
        for issue in issues
    ]


def lookup_current_value(ctx: PreflightContext, issue: ValidationIssue) -> str | None:
    row = issue.location.row
    column = issue.location.column
    if row is None or column is None:
        return None
    frame = source_frame_for_issue(ctx, issue)
    lookup_column = raw_column_name(frame, column)
    if frame is None or "source_row" not in frame.columns or lookup_column is None:
        return None
    matching = frame.loc[frame["source_row"] == row, [lookup_column]]
    if matching.empty:
        return None
    value = matching.iloc[0, 0]
    if pd.isna(value):
        return None
    return str(value).strip()


def source_frame_for_issue(
    ctx: PreflightContext,
    issue: ValidationIssue,
) -> pd.DataFrame | None:
    match issue.location.file:
        case SourceFile.PROMOTION_PLAN:
            return ctx.promotions
        case SourceFile.PRODUCT_MASTER:
            return ctx.products
        case SourceFile.INVENTORY:
            return ctx.inventory
        case _:
            return None


def raw_column_name(frame: pd.DataFrame | None, column: str) -> str | None:
    if frame is None:
        return None
    candidate = f"{column}_raw"
    if candidate in frame.columns:
        return candidate
    if column in frame.columns:
        return column
    return None


def suggest_value(ctx: PreflightContext, issue: ValidationIssue) -> str | None:
    return SUGGESTERS.get(issue.code, suggest_none)(ctx, issue)


def suggest_none(_ctx: PreflightContext, _issue: ValidationIssue) -> str | None:
    return None


def suggest_extreme_discount_rate(
    ctx: PreflightContext,
    issue: ValidationIssue,
) -> str | None:
    if issue.location.row is None:
        return None
    matching = ctx.joined.loc[ctx.joined["source_row"] == issue.location.row, ["normal_price"]]
    if matching.empty:
        return None
    normal_price = float(str(matching.iloc[0, 0]))
    threshold_price = math.floor(normal_price * (1 - ctx.thresholds.max_discount_rate)) + 1
    return str(threshold_price)


SUGGESTERS: dict[str, ChecklistSuggester] = {
    "EXTREME_DISCOUNT_RATE": suggest_extreme_discount_rate,
}
