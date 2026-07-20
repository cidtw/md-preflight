"""AI response plan when simulation expects sales decline.

Uses a fixed Korean SCM prompt. Store-data slots are filled from actual
evaluate/simulation parameters and calculated levers — never from design-doc
example prose alone.
"""

# urllib response types are untyped (Any); keep reportAny off for this adapter only.
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Protocol

from app.pipeline.domain_catalog import (
    ACCESSIBILITY,
    AVG_TICKET,
    ORDER_DAY_PATTERN,
    SERVICE_LEVEL,
    STORE_SIZE,
    STORE_TYPE,
    TRADE_AREA,
)
from app.pipeline.types import ParameterValue

logger = logging.getLogger(__name__)

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_MODEL = "grok-4.5"
_HTTP_TIMEOUT_S = 45.0

# Fixed system role — behavior only; store numbers come in the user message.
SYSTEM_PROMPT = (
    "당신은 편의점·슈퍼 공급망 관리(SCM) 및 재고 최적화 전문가입니다. "
    "제공된 [대상 매장 데이터]와 [시나리오 수치]만을 근거로 답합니다. "
    "데이터를 지어내지 말고, 수치가 없으면 '데이터 없음'으로 표시합니다. "
    "답변은 한국어로, 점주가 바로 실행할 수 있는 지침 형태(불릿·숫자 포함)로 작성합니다. "
    "판정 수치는 이미 계산된 시뮬레이션 결과를 존중하되, 운영 해석과 조정안을 제안합니다."
)

_USER_PROMPT_TEMPLATE = """\
당신은 편의점 공급망 관리(SCM) 및 재고 최적화 전문가입니다.
아래 제공하는 [대상 매장 데이터]를 바탕으로, **"인근 경쟁업체 등장으로 인한 매출 하락(수요 감소) 시나리오"**가 발생했을 때의 구체적인 ROP(재발주점) 및 발주 전략 조정 방안을 수립해 주세요.

---

### [대상 매장 데이터]
- 품목: {product_name}
- 매장 유형: {store_type_label} ({store_size_label}, 객단가 {avg_ticket_label})
- 입지 및 상권: {location_dong} ({accessibility_label}, {trade_area_label})
- 정확한 주소: {store_address}
- 현재 운영 지표:
  * 일 평균 판매량: 약 {daily_demand:g}개
  * 서비스 레벨 목표: {service_level_label}
  * 배송 리드타임: {lead_time:g}일 (입력 고정 · 출력에서 LT 변동 추천 없음)
  * 현재 ROP(발주 시점 재고): {rop_now:.1f}개 (안전재고 {ss_now:.1f}개 포함)
  * 현재 1회 발주량(Q): {q_now:g}개 (발주 요일·주기: {order_days_label})
  * 경쟁 수요 계수(현재): {comp_factor_now:.3f}

---

### [시나리오 조건 및 시뮬레이션 결과]
시나리오: {scenario_label} (충격 강도 {intensity_pct:.0f}%)
유효 수요 지수 변화: {delta_pct:+.1f}% (매출 하락 시나리오로 해석)
- 시나리오 후 일 유효 소진: 약 {daily_after:g}개
- 시나리오 후 ROP: {rop_after:.1f}개 · 안전재고 SS: {ss_after:.1f}개 · Q: {q_after:g}개
- 시나리오 후 LT: {lt_after:g}일 · 경쟁 수요 계수: {comp_factor_after:.3f}
- 엔진 요약: {plain_summary}

인근 경쟁 점포 압력·수요 이탈로 해당 매장 품목 수요(매출)가 위 수치처럼 감소하는 상황을 가정합니다.

이 조건 하에서 다음 질문에 대해 실무적이고 구체적인 대응 방안을 제안해 주세요.

1. **안전재고(SS) 및 ROP(재발주점) 조정안**
   - 매출 하락으로 일 판매량이 감소했을 때, 폐기율을 최소화하기 위해 안전재고(기존 {ss_now:.1f}개)와 ROP(기존 {rop_now:.1f}개)를 각각 몇 개 수준으로 낮추는 것이 적절한지 계산식이나 논리적 근거와 함께 제시해 주세요.
   - 서비스 레벨 목표({service_level_label})를 유지하면서도 과다 재고를 방지할 수 있는 타협점을 제안해 주세요.
   - 시뮬레이션이 제시한 시나리오 후 ROP/SS({rop_after:.1f}/{ss_after:.1f})를 참고하되, 현장 실행 단위(정수 개)로 정리해 주세요.

2. **발주 패턴 및 1회 발주량(Q) 최적화**
   - 현재 발주: {order_days_label}, 회당 약 {q_now:g}개.
   - 매출이 감소한 상황에서 이 주기를 유지하는 것이 유리할지, 회당 발주량(Q)을 더 줄이거나 주기를 변경하는 것이 매장 공간 관리와 폐기 방지 관점에서 유리할지 비교 분석해 주세요.
   - 시나리오 후 Q {q_after:g}개를 기준으로 권장안을 수치로 제시해 주세요.

3. **입지 및 상권 특성을 고려한 리스크 관리 방안**
   - 상권({trade_area_label})·접근성({accessibility_label}) 특성을 고려할 때, 전체 매출 하락 속에서도 특정 요일/시간대 수요 방어를 위해 남겨 두어야 할 최소 완충 재고 기준을 제시해 주세요.
   - 품목 '{product_name}' 특성(신선/상온 등)을 고려한 현장 운영 팁을 함께 제안해 주세요.

---
답변은 구체적인 수치(개수, 요일 등)를 포함하여 매장 점주가 바로 실행할 수 있는 지침 형태로 작성해 주세요.
"""


def _label(mapping: Mapping[str, str], key: object, default: str = "-") -> str:
    if key is None:
        return default
    return mapping.get(str(key), str(key) if key else default)


def _f(params: Mapping[str, ParameterValue], key: str, default: float = 0.0) -> float:
    raw = params.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        try:
            return float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default
    return float(raw)


def build_decline_user_prompt(
    *,
    parameters: Mapping[str, ParameterValue],
    scenario_label: str,
    intensity: float,
    delta_pct: float,
    plain_summary: str,
    baseline: Mapping[str, object],
    shocked: Mapping[str, object],
) -> str:
    """Fill the fixed template with real store + simulation numbers."""
    p = parameters
    product = str(p.get("product_name") or "대상 품목")
    store_type = _label(STORE_TYPE, p.get("store_type"))
    store_size = _label(STORE_SIZE, p.get("store_size"))
    ticket = _label(AVG_TICKET, p.get("avg_ticket"))
    trade = _label(TRADE_AREA, p.get("trade_area"))
    access = _label(ACCESSIBILITY, p.get("accessibility"))
    sl = _label(SERVICE_LEVEL, p.get("service_level", "sl_95"))
    pattern = str(p.get("order_day_pattern", "auto"))
    pattern_label = ORDER_DAY_PATTERN.get(pattern, pattern)
    order_days = str(baseline.get("order_days_label") or pattern_label)
    # Prefer shocked order label if present on side models via extra fields — use pattern only.
    if baseline.get("order_days_from_calc"):
        order_days = str(baseline["order_days_from_calc"])

    location = str(p.get("location_dong") or "-")
    address = str(p.get("store_address") or "미입력(행정동 경로)")
    if not p.get("use_precise_location"):
        address = "미사용(행정동 경로)"

    daily_base = _side_float(baseline, "daily_demand")
    if daily_base <= 0:
        daily_base = _f(p, "daily_demand", 0.0)
    lead = _side_float(baseline, "standard_lead_time_days")
    if lead <= 0:
        lead = _f(p, "standard_lead_time_days", 2.0)
    daily_after = _side_float(shocked, "effective_daily_demand")
    if daily_after <= 0:
        daily_after = _side_float(shocked, "daily_demand")

    return _USER_PROMPT_TEMPLATE.format(
        product_name=product,
        store_type_label=store_type,
        store_size_label=store_size,
        avg_ticket_label=ticket,
        location_dong=location,
        accessibility_label=access,
        trade_area_label=trade,
        store_address=address,
        daily_demand=daily_base,
        service_level_label=sl,
        lead_time=lead,
        rop_now=_side_float(baseline, "recommended_rop"),
        ss_now=_side_float(baseline, "store_safety_stock"),
        q_now=_side_float(baseline, "suggested_order_qty"),
        order_days_label=order_days,
        comp_factor_now=_side_float(baseline, "competition_demand_factor", 1.0),
        scenario_label=scenario_label,
        intensity_pct=max(0.0, min(1.0, intensity)) * 100,
        delta_pct=delta_pct,
        daily_after=daily_after,
        rop_after=_side_float(shocked, "recommended_rop"),
        ss_after=_side_float(shocked, "store_safety_stock"),
        q_after=_side_float(shocked, "suggested_order_qty"),
        lt_after=_side_float(shocked, "standard_lead_time_days"),
        comp_factor_after=_side_float(shocked, "competition_demand_factor", 1.0),
        plain_summary=plain_summary,
    )


def fallback_decline_advice(
    *,
    delta_pct: float,
    rop_now: float,
    rop_after: float,
    ss_now: float,
    ss_after: float,
    q_now: float,
    q_after: float,
) -> str:
    """Deterministic ops tips when AI is unavailable."""
    return (
        "### AI 대응 방안 (로컬 폴백 · API 키 없음 또는 호출 실패)\n\n"
        f"유효 수요 지수 약 **{delta_pct:+.1f}%** 로 매출 하락이 예상됩니다. "
        "아래는 엔진 수치에 맞춘 즉시 실행 가이드입니다.\n\n"
        "1. **SS·ROP**\n"
        f"   - 안전재고: {ss_now:.1f}개 → 목표 **{ss_after:.1f}개** 부근으로 단계 하향 "
        f"(한 번에 전량 삭감보다 1~2주 관찰).\n"
        f"   - ROP: {rop_now:.1f}개 → **{rop_after:.1f}개** 수준을 발주 트리거로 재설정.\n"
        "   - 서비스 레벨을 유지하려면 급격한 ROP 하향보다 판매 추세 1주 확인 후 재조정.\n\n"
        "2. **발주 패턴·Q**\n"
        f"   - 1회 발주량: {q_now:g}개 → **{q_after:g}개** 로 줄여 폐기·공간 부담을 완화.\n"
        "   - 창고가 협소하면 주 횟수는 유지하고 Q만 축소하는 편이 품절 방어에 유리한 경우가 많습니다.\n\n"
        "3. **현장 운영**\n"
        "   - 피크 요일 직전 소량 보충, 비피크는 진열 면적·발주 억제.\n"
        "   - 냉장 품목은 유통기한 FIFO·프로모션 연동으로 폐기 최소화.\n\n"
        "> SpaceXAI(`XAI_API_KEY`)를 설정하면 동일 프롬프트로 매장 맞춤 장문 대응안이 생성됩니다."
    )


class ChatFn(Protocol):
    def __call__(
        self,
        *,
        api_key: str,
        system: str,
        user: str,
        model: str,
    ) -> str: ...


def _side_float(side: Mapping[str, object], key: str, default: float = 0.0) -> float:
    raw = side.get(key, default)
    if isinstance(raw, bool):
        return default
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return default
    return default


def call_xai_chat(
    *,
    api_key: str,
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
    timeout: float = _HTTP_TIMEOUT_S,
) -> str:
    """POST /v1/chat/completions (OpenAI-compatible SpaceXAI / xAI)."""
    payload = {
        "model": model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        XAI_CHAT_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "md-preflight-rop/0.3",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw_bytes = bytes(resp.read())
    data: object = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(data, dict):
        msg = "Unexpected xAI response type"
        raise TypeError(msg)
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        msg = "xAI response missing choices"
        raise RuntimeError(msg)
    first = choices[0]
    if not isinstance(first, dict):
        msg = "Invalid choice"
        raise RuntimeError(msg)
    message = first.get("message")
    if not isinstance(message, dict):
        msg = "Invalid message"
        raise RuntimeError(msg)
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        msg = "Empty assistant content"
        raise RuntimeError(msg)
    return content.strip()


def generate_decline_advice(
    *,
    parameters: Mapping[str, ParameterValue],
    scenario_label: str,
    intensity: float,
    delta_pct: float,
    plain_summary: str,
    baseline: Mapping[str, object],
    shocked: Mapping[str, object],
    api_key: str | None,
    model: str = DEFAULT_MODEL,
    chat_fn: ChatFn | Callable[..., str] | None = None,
) -> tuple[str, bool, str | None]:
    """Return (advice_markdown, ai_used, error_note)."""
    user_prompt = build_decline_user_prompt(
        parameters=parameters,
        scenario_label=scenario_label,
        intensity=intensity,
        delta_pct=delta_pct,
        plain_summary=plain_summary,
        baseline=baseline,
        shocked=shocked,
    )
    if not api_key:
        text = fallback_decline_advice(
            delta_pct=delta_pct,
            rop_now=_side_float(baseline, "recommended_rop"),
            rop_after=_side_float(shocked, "recommended_rop"),
            ss_now=_side_float(baseline, "store_safety_stock"),
            ss_after=_side_float(shocked, "store_safety_stock"),
            q_now=_side_float(baseline, "suggested_order_qty"),
            q_after=_side_float(shocked, "suggested_order_qty"),
        )
        return text, False, "XAI_API_KEY 미설정 — 폴백 가이드 사용"

    try:
        if chat_fn is not None:
            content = chat_fn(
                api_key=api_key,
                system=SYSTEM_PROMPT,
                user=user_prompt,
                model=model,
            )
        else:
            content = call_xai_chat(
                api_key=api_key,
                system=SYSTEM_PROMPT,
                user=user_prompt,
                model=model,
            )
        return content, True, None
    except (urllib.error.URLError, TimeoutError, TypeError, ValueError, RuntimeError, OSError) as exc:
        logger.warning("decline AI advice failed: %s", exc)
        text = fallback_decline_advice(
            delta_pct=delta_pct,
            rop_now=_side_float(baseline, "recommended_rop"),
            rop_after=_side_float(shocked, "recommended_rop"),
            ss_now=_side_float(baseline, "store_safety_stock"),
            ss_after=_side_float(shocked, "store_safety_stock"),
            q_now=_side_float(baseline, "suggested_order_qty"),
            q_after=_side_float(shocked, "suggested_order_qty"),
        )
        return text, False, f"AI 호출 실패 — 폴백 사용: {exc}"
