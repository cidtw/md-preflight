"""What-if competition response simulation (deterministic, no live re-geo).

Given a completed evaluate calc (or parameters + shock), estimates how own-store
sales proxy and ROP levers move when:
  - own store improves fill (higher ROP / service)
  - competitor pressure rises (more saturation)
  - own LT deteriorates (logistics delay → buffer / weak demand)

Does not claim calibrated market-share; narratives stay relative and indexed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.pipeline.analyze.decline_advice import generate_decline_advice
from app.pipeline.analyze.engine import analyze
from app.pipeline.input.template import validate_parameters
from app.pipeline.types import CalcBreakdown, GeoEnrichment, ParameterValue
SimScenario = Literal[
    "own_service_up",
    "competitor_pressure",
    "own_lt_stress",
    "own_demand_rebound",
]


class SimulationRequest(BaseModel):
    parameters: dict[str, ParameterValue] = Field(default_factory=dict)
    scenario: SimScenario = "own_service_up"
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)


class SimulationSide(BaseModel):
    label: str
    daily_demand: float
    effective_daily_demand: float
    recommended_rop: float
    store_safety_stock: float
    suggested_order_qty: float
    standard_lead_time_days: float
    competition_demand_factor: float
    competition_intensity: float
    order_days_label: str = ""


class SimulationResponse(BaseModel):
    scenario: SimScenario
    scenario_label: str
    intensity: float
    baseline: SimulationSide
    shocked: SimulationSide
    own_sales_index_delta_pct: float
    competitor_response_note: str
    guidance: list[str] = Field(default_factory=list)
    plain_summary: str
    technical_summary: str = ""
    # AI response plan when sales index declines (delta < 0).
    sales_decline: bool = False
    ai_advice: str | None = None
    ai_used: bool = False
    ai_note: str | None = None


_SCENARIO_LABEL: dict[SimScenario, str] = {
    "own_service_up": "내 매장 서비스·ROP 강화",
    "competitor_pressure": "경쟁 매장 공세(포화 심화)",
    "own_lt_stress": "내 매장 리드타임 스트레스",
    "own_demand_rebound": "내 매장 수요 반등(점유 회복)",
}


def _side(label: str, calc: CalcBreakdown) -> SimulationSide:
    return SimulationSide(
        label=label,
        daily_demand=calc.daily_demand,
        effective_daily_demand=calc.effective_daily_demand,
        recommended_rop=calc.recommended_rop,
        store_safety_stock=calc.store_safety_stock,
        suggested_order_qty=calc.suggested_order_qty,
        standard_lead_time_days=calc.standard_lead_time_days,
        competition_demand_factor=calc.competition_demand_factor,
        competition_intensity=calc.competition_intensity,
        order_days_label=calc.order_days_label or calc.order_frequency_label or "",
    )


def _apply_scenario(
    params: dict[str, ParameterValue],
    *,
    scenario: SimScenario,
    intensity: float,
) -> tuple[dict[str, ParameterValue], str]:
    """Mutate a copy of parameters to encode the shock (demand / LT / SL)."""
    out = dict(params)
    i = max(0.0, min(1.0, intensity))
    demand = float(out.get("daily_demand", 10) or 10)
    lt = float(out.get("standard_lead_time_days", 2) or 2)

    if scenario == "own_service_up":
        # Higher service level + slight demand reclaim from better fill.
        out["service_level"] = "sl_99" if i >= 0.45 else "sl_95"
        reclaim = 1.0 + 0.12 * i  # up to +12% demand proxy
        out["daily_demand"] = round(demand * reclaim, 4)
        note = (
            "서비스 레벨·재고 방어를 올려 품절 감소 → 일부 수요를 되찾는 시나리오"
        )
    elif scenario == "competitor_pressure":
        # Market saturation: demand leaks to competitors.
        leak = 1.0 - 0.28 * i  # up to -28%
        out["daily_demand"] = round(max(0.1, demand * leak), 4)
        out["consider_competition_saturation"] = True
        note = "경쟁 매장이 공격적으로 재고·프로모션을 강화해 수요가 빠져나가는 시나리오"
    elif scenario == "own_lt_stress":
        # Contract LT lengthens (stress) — ops pain; mild demand leak from stockouts.
        out["standard_lead_time_days"] = round(max(0.5, lt * (1.0 + 0.5 * i)), 2)
        out["daily_demand"] = round(max(0.1, demand * (1.0 - 0.1 * i)), 4)
        note = "공급 LT가 늘어 여유 재고 부담이 커지고, 품절 리스크로 수요가 일부 이탈"
    else:  # own_demand_rebound
        out["daily_demand"] = round(demand * (1.0 + 0.22 * i), 4)
        out["service_level"] = "sl_95"
        note = "입지·운영 개선으로 수요가 반등하는 낙관 시나리오"
    return out, note


def run_simulation(
    body: SimulationRequest,
    *,
    geo_override: GeoEnrichment | None = None,
    settings: Settings | None = None,
) -> SimulationResponse:
    cfg = settings if settings is not None else get_settings()
    base_params = dict(body.parameters)
    # Simulation is most meaningful with precise address + competition context,
    # but still runs without it (demand/LT shocks only).
    validated_base = validate_parameters(base_params)
    base_calc = analyze(validated_base, geo_override=geo_override)

    shocked_params, scenario_note = _apply_scenario(
        base_params,
        scenario=body.scenario,
        intensity=body.intensity,
    )
    validated_shock = validate_parameters(shocked_params)
    shock_calc = analyze(validated_shock, geo_override=geo_override)

    base_side = _side("현재", base_calc)
    shock_side = _side("시나리오", shock_calc)

    # Sales index proxy = effective demand (post competition/event).
    base_sales = max(1e-9, base_side.effective_daily_demand)
    shock_sales = shock_side.effective_daily_demand
    delta_pct = round((shock_sales / base_sales - 1.0) * 100.0, 2)

    if body.scenario == "competitor_pressure":
        competitor = (
            f"경쟁 측은 공세 강도 {body.intensity:.0%} 가정 하에 내 매장 유효 수요가 "
            f"{delta_pct:+.1f}% 변한 것으로 해석합니다. 대응으로 발주 주기 단축·"
            f"1회 발주량 재조정(현재 Q {base_side.suggested_order_qty:g} → "
            f"{shock_side.suggested_order_qty:g})을 검토하세요."
        )
    elif body.scenario == "own_service_up":
        competitor = (
            f"내 매장이 서비스·ROP를 강화하면(ROP {base_side.recommended_rop:.0f}→"
            f"{shock_side.recommended_rop:.0f}) 경쟁 점유 일부를 되찾을 수 있습니다. "
            f"유효 수요 지수 {delta_pct:+.1f}%. 경쟁 매장은 가격·판촉으로 재대응할 여지를 남깁니다."
        )
    elif body.scenario == "own_lt_stress":
        competitor = (
            f"LT 스트레스 시 여유 재고·ROP가 커지고(SS {base_side.store_safety_stock:.0f}→"
            f"{shock_side.store_safety_stock:.0f}) 자금·공간 부담이 증가합니다. "
            f"경쟁 매장은 정상 공급을 유지하며 수요를 흡수할 수 있습니다 ({delta_pct:+.1f}%)."
        )
    else:
        competitor = (
            f"수요 반등 시나리오에서 유효 수요 {delta_pct:+.1f}%. "
            f"경쟁 포화 옵션이 켜져 있으면 분산 계수가 여전히 하방 압력으로 작용합니다."
        )

    label = _SCENARIO_LABEL[body.scenario]
    plain = (
        f"[{label}] 강도 {body.intensity:.0%} · 유효 수요 {base_side.effective_daily_demand:g}→"
        f"{shock_side.effective_daily_demand:g}개/일 ({delta_pct:+.1f}%) · "
        f"ROP {base_side.recommended_rop:.0f}→{shock_side.recommended_rop:.0f}개. "
        f"{scenario_note}."
    )
    technical = (
        f"[{label}] 충격 강도 {body.intensity:.0%}. "
        f"유효 일 소진(D_eff) {base_side.effective_daily_demand:g}→"
        f"{shock_side.effective_daily_demand:g}개/일 ({delta_pct:+.1f}%). "
        f"재발주점(ROP) {base_side.recommended_rop:.1f}→{shock_side.recommended_rop:.1f}개, "
        f"안전재고(SS) {base_side.store_safety_stock:.1f}→{shock_side.store_safety_stock:.1f}개, "
        f"1회 발주량(Q) {base_side.suggested_order_qty:g}→{shock_side.suggested_order_qty:g}개, "
        f"리드타임(LT) {base_side.standard_lead_time_days:g}→"
        f"{shock_side.standard_lead_time_days:g}일. "
        f"경쟁 수요 계수 {base_side.competition_demand_factor:.3f}→"
        f"{shock_side.competition_demand_factor:.3f} "
        f"(강도 지수 {base_side.competition_intensity:.3f}→"
        f"{shock_side.competition_intensity:.3f}). "
        f"{scenario_note}."
    )
    guidance = list(validated_shock.guidance)
    if not bool(base_params.get("use_precise_location")):
        guidance.append(
            "정확한 주소·경쟁 포화 옵션을 켜면 시뮬레이션이 상권 경쟁 계수와 함께 해석됩니다.",
        )

    # Sales-decline → fixed-prompt AI (or fallback) response plan.
    sales_decline = delta_pct < -0.05  # treat near-zero as no decline
    ai_advice: str | None = None
    ai_used = False
    ai_note: str | None = None
    if sales_decline:
        base_map = base_side.model_dump()
        base_map["order_days_from_calc"] = base_side.order_days_label
        shock_map = shock_side.model_dump()
        ai_advice, ai_used, ai_note = generate_decline_advice(
            parameters=base_params,
            scenario_label=label,
            intensity=body.intensity,
            delta_pct=delta_pct,
            plain_summary=plain,
            baseline=base_map,
            shocked=shock_map,
            api_key=cfg.xai_api_key,
            model=cfg.xai_model,
        )

    return SimulationResponse(
        scenario=body.scenario,
        scenario_label=label,
        intensity=body.intensity,
        baseline=base_side,
        shocked=shock_side,
        own_sales_index_delta_pct=delta_pct,
        competitor_response_note=competitor,
        guidance=guidance,
        plain_summary=plain,
        technical_summary=technical,
        sales_decline=sales_decline,
        ai_advice=ai_advice,
        ai_used=ai_used,
        ai_note=ai_note,
    )
