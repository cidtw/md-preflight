"""Stage 2 — internal calculation engine for adjusted LT / ROP."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.pipeline.analyze.geo_enrichment import (
    JsonFetch,
    disabled_enrichment,
    enrich_from_address,
)
from app.pipeline.analyze.knowledge_base import match_knowledge, store_safety_stock
from app.pipeline.analyze.scoring import max_rop_for_capa, score_store
from app.pipeline.domain_catalog import DEFAULT_BASE_SAFETY_FRAC, DEFAULT_STANDARD_LT
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
        api_key=settings.google_maps_api_key,
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
    )

    if "standard_lead_time_days" in p:
        standard_lt = max(0.5, _as_float(p["standard_lead_time_days"], 2.0))
    else:
        standard_lt = DEFAULT_STANDARD_LT.get(store_type, 2.0)

    recommended_lt = max(
        0.5,
        round(
            standard_lt
            + scores.accessibility_lt_delta_days
            + knowledge.logistics_delay_days,
            2,
        ),
    )
    lt_delta = round(recommended_lt - standard_lt, 2)

    base_frac = DEFAULT_BASE_SAFETY_FRAC.get(store_type, 0.35)
    base_safety = round(daily_demand * standard_lt * base_frac, 2)

    if "standard_rop" in p:
        standard_rop = max(0.0, _as_float(p["standard_rop"], 0.0))
    else:
        standard_rop = round(daily_demand * standard_lt + base_safety, 2)

    store_safety = store_safety_stock(
        safety_z=knowledge.safety_z_factor,
        recommended_lt=recommended_lt,
        demand_volatility=scores.demand_volatility,
        turnover_weight=scores.turnover_weight,
    )
    raw_rop = round(daily_demand * recommended_lt + store_safety, 2)

    capa_capped = False
    max_cap: float | None = None
    multi_order: str | None = None
    recommended_rop = raw_rop

    if scores.capa_score <= 2:
        max_cap = round(
            max_rop_for_capa(
                daily_demand=daily_demand,
                recommended_lt=recommended_lt,
                capa_score=scores.capa_score,
            ),
            2,
        )
        if raw_rop > max_cap:
            capa_capped = True
            recommended_rop = max_cap
            multi_order = (
                f"물류 창고 CAPA 점수 {scores.capa_score}/5(협소)로 계산 ROP "
                f"{raw_rop:.1f}개가 상한 {max_cap:.1f}개를 초과해 상한으로 고정했습니다. "
                f"화·목 등 차수 분할 소량 발주(다회 소량)로 전환하는 것을 권장합니다."
            )

    return CalcBreakdown(
        standard_lead_time_days=standard_lt,
        recommended_lead_time_days=recommended_lt,
        lead_time_delta_days=lt_delta,
        standard_rop=standard_rop,
        recommended_rop=recommended_rop,
        rop_delta=round(recommended_rop - standard_rop, 2),
        daily_demand=daily_demand,
        base_safety_stock=base_safety,
        store_safety_stock=store_safety,
        recommended_rop_raw=raw_rop,
        capa_capped=capa_capped,
        max_rop_cap=max_cap,
        multi_order_suggestion=multi_order,
        scores=scores,
        knowledge=knowledge,
        geo=geo,
    )
