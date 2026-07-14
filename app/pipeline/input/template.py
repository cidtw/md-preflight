"""Stage 1 - parameter template definition and validation."""

from __future__ import annotations

from collections.abc import Mapping

from app.core.errors import InputValidationError
from app.pipeline.types import (
    InputTemplate,
    ParameterSpec,
    ParameterValue,
    ValidatedInput,
)

# Placeholder template for the redesign skeleton.
# Real domain parameters are filled after research (see docs/redesign/board.md R0-R2).
DEFAULT_TEMPLATE = InputTemplate(
    id="generic-evaluate-v0",
    title="Generic evaluation (skeleton)",
    description=(
        "Placeholder parameter set for the modular pipeline. "
        "Replace with researched domain criteria before production use."
    ),
    version="0.1.0",
    parameters=[
        ParameterSpec(
            key="quality",
            label="Quality score",
            type="number",
            description="Subjective or measured quality in 0-100.",
            minimum=0.0,
            maximum=100.0,
        ),
        ParameterSpec(
            key="cost",
            label="Cost index",
            type="number",
            description="Relative cost index in 0-100 (lower is better after inversion).",
            minimum=0.0,
            maximum=100.0,
        ),
        ParameterSpec(
            key="risk",
            label="Risk index",
            type="number",
            description="Risk exposure in 0-100 (lower is better after inversion).",
            minimum=0.0,
            maximum=100.0,
        ),
        ParameterSpec(
            key="priority",
            label="Priority label",
            type="string",
            required=False,
            description="Optional tag for audit (does not affect score in skeleton).",
            allowed_values=["low", "medium", "high"],
        ),
    ],
)


def get_template() -> InputTemplate:
    return DEFAULT_TEMPLATE


def _as_number(key: str, value: ParameterValue) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputValidationError(f"Parameter '{key}' must be a number")
    return float(value)


def _as_string(key: str, value: ParameterValue) -> str:
    if not isinstance(value, str):
        raise InputValidationError(f"Parameter '{key}' must be a string")
    return value


def _as_boolean(key: str, value: ParameterValue) -> bool:
    if not isinstance(value, bool):
        raise InputValidationError(f"Parameter '{key}' must be a boolean")
    return value


def validate_parameters(
    raw: Mapping[str, ParameterValue],
    *,
    template: InputTemplate | None = None,
) -> ValidatedInput:
    """Validate and normalize client parameters against the public template."""
    spec = template or get_template()
    known = {p.key: p for p in spec.parameters}
    unknown = sorted(set(raw) - set(known))
    if unknown:
        raise InputValidationError(f"Unknown parameter(s): {', '.join(unknown)}")

    normalized: dict[str, ParameterValue] = {}
    for key, param in known.items():
        if key not in raw:
            if param.required:
                raise InputValidationError(f"Missing required parameter: '{key}'")
            continue
        value = raw[key]
        if param.type == "number":
            number = _as_number(key, value)
            if param.minimum is not None and number < param.minimum:
                raise InputValidationError(
                    f"Parameter '{key}' must be >= {param.minimum}",
                )
            if param.maximum is not None and number > param.maximum:
                raise InputValidationError(
                    f"Parameter '{key}' must be <= {param.maximum}",
                )
            normalized[key] = number
        elif param.type == "string":
            text = _as_string(key, value)
            if param.allowed_values is not None and text not in param.allowed_values:
                allowed = ", ".join(param.allowed_values)
                raise InputValidationError(
                    f"Parameter '{key}' must be one of: {allowed}",
                )
            normalized[key] = text
        else:
            normalized[key] = _as_boolean(key, value)

    return ValidatedInput(
        template_id=spec.id,
        template_version=spec.version,
        parameters=normalized,
    )
