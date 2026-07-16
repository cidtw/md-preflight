"""Stage 2 — internal calculation engine for ROP and operational levers.

Lead time is treated as a fixed contractual/standard input. Accessibility and
KB logistics signals become buffer stock and order-policy recommendations, not
a new "recommended LT".
"""

from __future__ import annotations

from app.core.config import Settings, get_settings
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
    return enrich_from_address(
        address,
        api_key=settings.kakao_rest_api_key,
        radius_m=settings.geo_radius_m,
        fetch=fetch,
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
    knowledge = match_knowledge(
        location_dong=location_dong,
        product_name=product_name,
        trade_area=trade_area,
        accessibility=accessibility,
        scores=scores,
        foot_traffic_index=geo.foot_traffic_index,
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
    logistics_risk_days = round(
        max(0.0, scores.accessibility_lt_delta_days + knowledge.logistics_delay_days),
        2,
    )
    logistics_buffer = round(daily_demand * logistics_risk_days, 2)

    base_frac = DEFAULT_BASE_SAFETY_FRAC.get(channel_key, 0.35)
    base_safety = round(daily_demand * fixed_lt * base_frac, 2)

    if "standard_rop" in p:
        standard_rop = max(0.0, _as_float(p["standard_rop"], 0.0))
    else:
        standard_rop = round(daily_demand * fixed_lt + base_safety, 2)

    statistical_ss = store_safety_stock(
        safety_z=knowledge.safety_z_factor,
        lead_time_days=fixed_lt,
        demand_volatility=scores.demand_volatility,
        turnover_weight=scores.turnover_weight,
        daily_demand=daily_demand,
    )
    # Total safety stock = statistical SS + logistics risk buffer (units).
    store_safety = round(statistical_ss + logistics_buffer, 2)
    raw_rop = round(daily_demand * fixed_lt + store_safety, 2)

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
        daily_demand=daily_demand,
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
                daily_demand=daily_demand,
                recommended_lt=fixed_lt,
                capa_score=scores.capa_score,
            ),
            2,
        )
        if raw_rop > max_cap:
            capa_capped = True
            recommended_rop = max_cap
            # Keep ROP = D*LT + SS identity after cap: display effective SS.
            store_safety = round(
                max(0.0, recommended_rop - daily_demand * fixed_lt),
                2,
            )
        # Physical stock ceiling also bounds per-receipt order qty (cycle may exceed cover).
        if order_qty > max_cap:
            order_qty = max(1.0, round(max_cap, 1))
        if capa_capped or order_qty < order_qty_raw:
            if capa_capped:
                rop_part = (
                    f"계산 ROP {raw_rop:.1f}개가 상한 {max_cap:.1f}개를 초과해 "
                    f"상한으로 고정했습니다. "
                    f"표시 안전재고는 캡 반영 유효값 {store_safety:.1f}개 "
                    f"(캡 전 통계+버퍼 {statistical_ss + logistics_buffer:.1f}개). "
                )
            else:
                rop_part = f"발주량 상한 {max_cap:.1f}개를 적용했습니다. "
            if order_qty < order_qty_raw:
                qty_part = (
                    f"1회 발주량 {order_qty_raw:g}개 → CAPA 상한 {order_qty:g}개로 절사. "
                )
            else:
                qty_part = f"1회 약 {order_qty:g}개 수준. "
            multi_order = (
                f"물류 창고 CAPA 점수 {scores.capa_score}/5(협소)로 {rop_part}"
                f"{qty_part}발주 요일 {days_label} · 다회 소량 발주를 권장합니다."
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
        base_safety_stock=base_safety,
        store_safety_stock=store_safety,
        order_cycle_days=order_cycle,
        suggested_order_qty=order_qty,
        order_frequency_label=order_label,
        recommended_rop_raw=raw_rop,
        capa_capped=capa_capped,
        max_rop_cap=max_cap,
        multi_order_suggestion=multi_order,
        scores=scores,
        knowledge=knowledge,
        geo=geo,
    )
