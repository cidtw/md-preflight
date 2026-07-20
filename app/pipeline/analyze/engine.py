"""Stage 2 — internal calculation engine for ROP and operational levers.

Lead time is treated as a fixed contractual/standard input. Accessibility and
KB logistics signals become buffer stock and order-policy recommendations, not
a new "recommended LT".
"""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.pipeline.analyze.event_foot_traffic import blend_fti_with_event
from app.pipeline.analyze.geo_enrichment import (
    JsonFetch,
    disabled_enrichment,
    enrich_from_address,
)
from app.pipeline.analyze.knowledge_base import (
    match_knowledge,
    store_safety_stock,
    suggest_order_policy,
)
from app.pipeline.analyze.scoring import max_rop_for_capa, score_store
from app.pipeline.domain_catalog import (
    DEFAULT_BASE_SAFETY_FRAC,
    DEFAULT_STANDARD_LT,
    ORDER_DAY_PATTERN,
    SERVICE_LEVEL,
    SIZE_TO_CHANNEL,
)
from app.pipeline.types import CalcBreakdown, GeoEnrichment, ValidatedInput

# Global band on D_eff after event x competition (and future multipliers).
# Module-level event (+35%) / competition (-40%) already stay inside this band;
# the clamp is a safety net if geo multipliers or future stages expand.
D_EFF_MIN_FRAC = 0.5
D_EFF_MAX_FRAC = 2.0


def _as_float(value: object, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _as_str(value: object) -> str:
    return str(value)


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _resolve_geo(
    validated: ValidatedInput,
    *,
    settings: Settings,
    fetch: JsonFetch | None,
) -> GeoEnrichment:
    p = validated.parameters
    use_precise = _as_bool(p.get("use_precise_location"), False)
    if not use_precise:
        return disabled_enrichment()
    address = _as_str(p.get("store_address", "")).strip()
    scan_events = _as_bool(p.get("consider_temp_foot_traffic"), False)
    scan_competition = _as_bool(p.get("consider_competition_saturation"), False)
    store_type = _as_str(p.get("store_type", "convenience"))
    return enrich_from_address(
        address,
        api_key=settings.kakao_rest_api_key,
        radius_m=settings.geo_radius_m,
        fetch=fetch,
        scan_events=scan_events,
        scan_competition=scan_competition,
        store_type=store_type,
    )


def analyze(
    validated: ValidatedInput,
    *,
    settings: Settings | None = None,
    geo_fetch: JsonFetch | None = None,
    geo_override: GeoEnrichment | None = None,
) -> CalcBreakdown:
    cfg = settings if settings is not None else get_settings()
    p = validated.parameters
    store_type = _as_str(p["store_type"])
    store_size = _as_str(p["store_size"])
    avg_ticket = _as_str(p["avg_ticket"])
    trade_area = _as_str(p["trade_area"])
    accessibility = _as_str(p["accessibility"])
    location_dong = _as_str(p["location_dong"])
    product_name = _as_str(p["product_name"])
    daily_demand = _as_float(p["daily_demand"], 1.0)
    service_level = _as_str(p.get("service_level", "sl_95"))
    if service_level not in SERVICE_LEVEL:
        service_level = "sl_95"
    order_pattern_in = _as_str(p.get("order_day_pattern", "auto"))
    if order_pattern_in not in ORDER_DAY_PATTERN:
        order_pattern_in = "auto"

    scores = score_store(
        store_size=store_size,
        avg_ticket=avg_ticket,
        trade_area=trade_area,
        accessibility=accessibility,
    )
    geo = (
        geo_override
        if geo_override is not None
        else _resolve_geo(validated, settings=cfg, fetch=geo_fetch)
    )
    # Temporary event-crowd uplift blends into FTI for Z context and scales demand.
    fti_for_kb = blend_fti_with_event(
        geo.foot_traffic_index,
        geo.event_foot_traffic_uplift,
    )
    knowledge = match_knowledge(
        location_dong=location_dong,
        product_name=product_name,
        trade_area=trade_area,
        accessibility=accessibility,
        scores=scores,
        foot_traffic_index=fti_for_kb,
        service_level=service_level,
    )

    # Defaults follow size band (channel map), not store_type — size/ticket win on conflict.
    channel_key = SIZE_TO_CHANNEL.get(store_size, store_type)

    # LT is a product-specific INPUT (kept). Output never recommends changing it.
    if "standard_lead_time_days" in p:
        standard_lt = max(0.5, _as_float(p["standard_lead_time_days"], 2.0))
    else:
        standard_lt = DEFAULT_STANDARD_LT.get(channel_key, 2.0)

    fixed_lt = standard_lt
    # Event uplift (≥1) then competition saturation (≤1). Standard comparison uses base D.
    mult = max(1.0, float(geo.event_demand_multiplier or 1.0))
    comp_factor = float(geo.competition_demand_factor or 1.0)
    if not geo.competition_scan_enabled:
        comp_factor = 1.0
    comp_factor = min(1.0, max(0.0, comp_factor))
    comp_intensity = (
        float(geo.competition_intensity) if geo.competition_scan_enabled else 0.0
    )
    uncapped_demand = round(daily_demand * mult * comp_factor, 4)
    lo = round(daily_demand * D_EFF_MIN_FRAC, 4)
    hi = round(daily_demand * D_EFF_MAX_FRAC, 4)
    effective_demand = round(min(hi, max(lo, uncapped_demand)), 4)
    demand_clamped = abs(effective_demand - uncapped_demand) > 1e-9
    event_uplift_frac = round(max(0.0, mult - 1.0), 4)
    competition_cut_frac = round(max(0.0, 1.0 - comp_factor), 4)

    # R16: optional measured logistics delay replaces KB residual (hash/table L3).
    # Accessibility risk days still apply on top.
    measured_delay: float | None = None
    logistics_delay_mode = "proxy_kb"
    if "measured_logistics_delay_days" in p:
        measured_delay = max(0.0, _as_float(p["measured_logistics_delay_days"], 0.0))
        logistics_delay_mode = "measured_delay"
        delay_component = measured_delay
    else:
        delay_component = knowledge.logistics_delay_days

    logistics_risk_days = round(
        max(0.0, scores.accessibility_lt_delta_days + delay_component),
        2,
    )
    # Logistics buffer and SS scale with event-adjusted demand when uplift is on.
    logistics_buffer = round(effective_demand * logistics_risk_days, 2)

    base_frac = DEFAULT_BASE_SAFETY_FRAC.get(channel_key, 0.35)
    base_safety = round(daily_demand * fixed_lt * base_frac, 2)

    if "standard_rop" in p:
        standard_rop = max(0.0, _as_float(p["standard_rop"], 0.0))
    else:
        # Baseline standard stays on unadjusted demand (no temporary event).
        standard_rop = round(daily_demand * fixed_lt + base_safety, 2)

    # R16: optional POS daily demand sigma replaces vol-score proxy (L3).
    demand_sigma: float | None = None
    ss_mode = "proxy_vol"
    if "demand_sigma_daily" in p:
        demand_sigma = max(0.0, _as_float(p["demand_sigma_daily"], 0.0))
        ss_mode = "measured_sigma"

    statistical_ss = store_safety_stock(
        safety_z=knowledge.safety_z_factor,
        lead_time_days=fixed_lt,
        demand_volatility=scores.demand_volatility,
        turnover_weight=scores.turnover_weight,
        daily_demand=effective_demand,
        demand_sigma_daily=demand_sigma,
    )
    # Total safety stock = statistical SS + logistics risk buffer (units).
    store_safety = round(statistical_ss + logistics_buffer, 2)
    raw_rop = round(effective_demand * fixed_lt + store_safety, 2)

    (
        order_cycle,
        order_qty,
        order_label,
        resolved_pattern,
        days_label,
        pattern_auto,
    ) = suggest_order_policy(
        capa_score=scores.capa_score,
        demand_concentration=scores.demand_concentration,
        daily_demand=effective_demand,
        lead_time_days=fixed_lt,
        order_day_pattern=order_pattern_in,
    )

    capa_capped = False
    max_cap: float | None = None
    multi_order: str | None = None
    recommended_rop = raw_rop
    order_qty_raw = order_qty

    if scores.capa_score <= 2:
        max_cap = round(
            max_rop_for_capa(
                daily_demand=effective_demand,
                recommended_lt=fixed_lt,
                capa_score=scores.capa_score,
            ),
            2,
        )
        if raw_rop > max_cap:
            capa_capped = True
            recommended_rop = max_cap
            # Keep ROP = D_eff*LT + SS identity after cap: display effective SS.
            store_safety = round(
                max(0.0, recommended_rop - effective_demand * fixed_lt),
                2,
            )
        # Physical stock ceiling also bounds per-receipt order qty (cycle may exceed cover).
        # Do not floor at 1.0 — low demand can yield max_cap < 1 and that floor would
        # leave Q above MaxCap (review: CAPA Q clamp invariant).
        if order_qty > max_cap:
            order_qty = max_cap
        if capa_capped or order_qty < order_qty_raw:
            if capa_capped:
                rop_part = (
                    f"한 번에 쌓아 두기엔 많아 보여 발주 기준(재고 {raw_rop:.0f}개)을 "
                    f"매장에 맞는 상한 {max_cap:.0f}개로 낮췄습니다. "
                )
            else:
                rop_part = (
                    f"창고가 좁아 1회 발주량 상한 {max_cap:.0f}개를 적용했습니다. "
                )
            if order_qty < order_qty_raw:
                qty_part = (
                    f"1회 발주량도 {order_qty_raw:g}개 → {order_qty:g}개로 줄였습니다. "
                )
            else:
                qty_part = f"1회 약 {order_qty:g}개 수준입니다. "
            multi_order = (
                f"매장·창고 공간이 넉넉하지 않습니다. {rop_part}"
                f"{qty_part}"
                f"대신 '{days_label}'처럼 자주 조금씩 넣는 편이 안전합니다. "
                f"공간 상한으로 한 번에 쌓는 재고를 줄이면 이론상 품절 여유"
                f"(서비스 레벨)는 다소 줄 수 있어, 발주 횟수로 상쇄하는 "
                f"운영 타협(trade-off)입니다."
            )

    return CalcBreakdown(
        standard_lead_time_days=fixed_lt,
        recommended_lead_time_days=fixed_lt,
        lead_time_delta_days=0.0,
        lead_time_fixed=True,
        logistics_risk_days=logistics_risk_days,
        logistics_buffer_units=logistics_buffer,
        statistical_safety_stock=statistical_ss,
        service_level=service_level,
        service_level_label=SERVICE_LEVEL[service_level],
        order_day_pattern_input=order_pattern_in,
        order_day_pattern=resolved_pattern,
        order_days_label=days_label,
        order_pattern_auto=pattern_auto,
        standard_rop=standard_rop,
        recommended_rop=recommended_rop,
        rop_delta=round(recommended_rop - standard_rop, 2),
        daily_demand=daily_demand,
        effective_daily_demand=effective_demand,
        effective_daily_demand_uncapped=uncapped_demand,
        effective_demand_clamped=demand_clamped,
        event_demand_uplift_frac=event_uplift_frac,
        competition_intensity=round(comp_intensity, 4),
        competition_demand_factor=round(comp_factor, 4),
        competition_demand_cut_frac=competition_cut_frac,
        base_safety_stock=base_safety,
        store_safety_stock=store_safety,
        order_cycle_days=order_cycle,
        suggested_order_qty=order_qty,
        order_frequency_label=order_label,
        ss_mode=ss_mode,
        demand_sigma_daily=demand_sigma,
        logistics_delay_mode=logistics_delay_mode,
        measured_logistics_delay_days=measured_delay,
        recommended_rop_raw=raw_rop,
        capa_capped=capa_capped,
        max_rop_cap=max_cap,
        multi_order_suggestion=multi_order,
        scores=scores,
        knowledge=knowledge,
        geo=geo,
    )
