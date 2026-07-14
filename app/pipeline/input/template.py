"""Stage 1 — ROP service input template and validation."""

from __future__ import annotations

from collections.abc import Mapping

from app.core.errors import InputValidationError
from app.pipeline.domain_catalog import (
    ACCESSIBILITY,
    AVG_TICKET,
    STORE_SIZE,
    STORE_TYPE,
    STORE_TYPE_SIZE_EXPECT,
    STORE_TYPE_TICKET_EXPECT,
    TRADE_AREA,
)
from app.pipeline.types import (
    InputTemplate,
    ParameterOption,
    ParameterSpec,
    ParameterValue,
    ValidatedInput,
)

TEMPLATE_ID = "rop-adjust-v1"
TEMPLATE_VERSION = "1.1.0"


def _opts(mapping: dict[str, str]) -> list[ParameterOption]:
    return [ParameterOption(value=k, label=v) for k, v in mapping.items()]


def get_template() -> InputTemplate:
    return InputTemplate(
        id=TEMPLATE_ID,
        title="매장 특화 ROP 재조정",
        description=(
            "매장·상권·접근성 파라미터와 품목·일평균 소진량을 입력하면 "
            "Lead Time / Re-Order Point 재조정값과 근거 리포트를 반환합니다. "
            "정확한 위치 사용 시 Google Maps로 주변 유동 유발 시설을 점수에 반영합니다."
        ),
        version=TEMPLATE_VERSION,
        parameters=[
            ParameterSpec(
                key="product_name",
                label="재고 최적화 대상 품목",
                type="string",
                description="예: 냉장 간편식, 상온 즉석밥",
            ),
            ParameterSpec(
                key="store_type",
                label="매장 유형",
                type="string",
                options=_opts(STORE_TYPE),
                allowed_values=list(STORE_TYPE),
            ),
            ParameterSpec(
                key="store_size",
                label="매장 규모 (연면적)",
                type="string",
                description="유형과 불일치 시 규모 선택이 연산 기준이 됩니다.",
                options=_opts(STORE_SIZE),
                allowed_values=list(STORE_SIZE),
            ),
            ParameterSpec(
                key="avg_ticket",
                label="객단가",
                type="string",
                description="유형과 불일치 시 객단가 선택이 연산 기준이 됩니다.",
                options=_opts(AVG_TICKET),
                allowed_values=list(AVG_TICKET),
            ),
            ParameterSpec(
                key="location_dong",
                label="입지 주소 (행정동)",
                type="string",
                description="상세 번지 불필요. 예: 서울시 강남구 역삼1동",
            ),
            ParameterSpec(
                key="use_precise_location",
                label="정확한 위치 사용",
                type="boolean",
                required=False,
                description=(
                    "체크 시 도로명 주소를 받아 Google Maps로 주변 지하철·버스·"
                    "랜드마크 등 유동 유발 요소를 점수에 반영합니다."
                ),
            ),
            ParameterSpec(
                key="store_address",
                label="정확한 매장 주소",
                type="string",
                required=False,
                description="정확한 위치 사용 시에만 필수. 예: 서울시 마포구 양화로 45",
            ),
            ParameterSpec(
                key="trade_area",
                label="핵심 타겟 상권 유형",
                type="string",
                options=_opts(TRADE_AREA),
                allowed_values=list(TRADE_AREA),
            ),
            ParameterSpec(
                key="accessibility",
                label="매장 정면 접근성",
                type="string",
                options=_opts(ACCESSIBILITY),
                allowed_values=list(ACCESSIBILITY),
            ),
            ParameterSpec(
                key="daily_demand",
                label="일평균 소진량 (개)",
                type="number",
                description="품목 일평균 판매/소진 수량",
                minimum=0.1,
                maximum=100000.0,
            ),
            ParameterSpec(
                key="standard_lead_time_days",
                label="사내 표준 Lead Time (일)",
                type="number",
                required=False,
                description="미입력 시 매장 유형 채널 기본값을 사용합니다.",
                minimum=0.5,
                maximum=30.0,
            ),
            ParameterSpec(
                key="standard_rop",
                label="사내/업계 표준 ROP (개)",
                type="number",
                required=False,
                description="미입력 시 표준 LT·기본 안전재고로 산정합니다.",
                minimum=0.0,
                maximum=1000000.0,
            ),
        ],
    )


def _as_number(key: str, value: ParameterValue) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputValidationError(f"Parameter '{key}' must be a number")
    return float(value)


def _as_string(key: str, value: ParameterValue) -> str:
    if not isinstance(value, str):
        raise InputValidationError(f"Parameter '{key}' must be a string")
    text = value.strip()
    if not text:
        raise InputValidationError(f"Parameter '{key}' must not be empty")
    return text


def _as_bool(key: str, value: ParameterValue) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off", ""}:
            return False
    raise InputValidationError(f"Parameter '{key}' must be a boolean")


def _choice(key: str, value: ParameterValue, allowed: dict[str, str]) -> str:
    text = _as_string(key, value)
    if text not in allowed:
        options = ", ".join(allowed)
        raise InputValidationError(f"Parameter '{key}' must be one of: {options}")
    return text


def _build_guidance(store_type: str, store_size: str, avg_ticket: str) -> list[str]:
    notes: list[str] = []
    size_expect = STORE_TYPE_SIZE_EXPECT.get(store_type, frozenset())
    if store_size not in size_expect:
        size_label = STORE_SIZE[store_size]
        notes.append(
            "매장 유형과 연면적(규모) 정보가 상이합니다. "
            + f"연산에는 선택하신 매장 규모 '{size_label}'를 기준으로 적용합니다.",
        )
    ticket_expect = STORE_TYPE_TICKET_EXPECT.get(store_type, frozenset())
    if avg_ticket not in ticket_expect:
        ticket_label = AVG_TICKET[avg_ticket]
        notes.append(
            "매장 유형과 객단가 정보가 상이합니다. "
            + f"연산에는 선택하신 객단가 '{ticket_label}'를 기준으로 적용합니다.",
        )
    return notes


def validate_parameters(
    raw: Mapping[str, ParameterValue],
    *,
    template: InputTemplate | None = None,
) -> ValidatedInput:
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
        elif param.type == "boolean":
            normalized[key] = _as_bool(key, value)
        elif param.allowed_values is not None:
            allowed_map = {
                "store_type": STORE_TYPE,
                "store_size": STORE_SIZE,
                "avg_ticket": AVG_TICKET,
                "trade_area": TRADE_AREA,
                "accessibility": ACCESSIBILITY,
            }.get(key)
            if allowed_map is None:
                text = _as_string(key, value)
                if text not in param.allowed_values:
                    raise InputValidationError(f"Parameter '{key}' has invalid value")
                normalized[key] = text
            else:
                normalized[key] = _choice(key, value, allowed_map)
        else:
            # Optional strings may be omitted; if present must be non-empty unless blank skip
            if key == "store_address" and isinstance(value, str) and not value.strip():
                continue
            normalized[key] = _as_string(key, value)

    use_precise = bool(normalized.get("use_precise_location", False))
    if not use_precise:
        normalized["use_precise_location"] = False
        _ = normalized.pop("store_address", None)
    else:
        normalized["use_precise_location"] = True
        if "store_address" not in normalized:
            raise InputValidationError(
                "정확한 위치 사용 시 'store_address'(정확한 매장 주소)가 필요합니다.",
            )

    store_type = str(normalized["store_type"])
    store_size = str(normalized["store_size"])
    avg_ticket = str(normalized["avg_ticket"])
    guidance = _build_guidance(store_type, store_size, avg_ticket)

    return ValidatedInput(
        template_id=spec.id,
        template_version=spec.version,
        parameters=normalized,
        guidance=guidance,
    )
