from __future__ import annotations

from app.core.rule_config import RuleThresholds
from app.domain.context import PreflightContext
from app.rules import RULES, compute_rule_set_version
from app.rules.base import Rule
from app.rules.margin_rate import LOW_MARGIN_RATE_RULE
from app.services.validation_engine import validate_context


def test_compute_rule_set_version_is_deterministic() -> None:
    thresholds = RuleThresholds()

    first = compute_rule_set_version(thresholds)
    second = compute_rule_set_version(thresholds)

    assert first == second


def test_compute_rule_set_version_changes_with_thresholds() -> None:
    default_thresholds = RuleThresholds()
    custom_thresholds = RuleThresholds(min_margin_rate=0.1)

    assert compute_rule_set_version(default_thresholds) != compute_rule_set_version(
        custom_thresholds
    )


def test_compute_rule_set_version_changes_with_rule_set() -> None:
    thresholds = RuleThresholds()
    subset: list[Rule] = [LOW_MARGIN_RATE_RULE]

    assert compute_rule_set_version(thresholds, rules=RULES) != compute_rule_set_version(
        thresholds, rules=subset
    )


def test_validate_context_stamps_report_with_rule_set_version(
    sample_context: PreflightContext,
) -> None:
    report = validate_context(sample_context)

    assert report.rule_set_version == compute_rule_set_version(
        sample_context.thresholds,
        rules=RULES,
    )
