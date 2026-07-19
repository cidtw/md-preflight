"""Deterministic knowledge-base matcher (Agent-AI shaped, no live model).

Produces location/product/trade-aware signals and narrative notes derived from
inputs so outputs are never a fixed copy of the design-doc examples.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.pipeline.domain_catalog import (
    ACCESSIBILITY,
    ORDER_DAY_PATTERN,
    ORDER_PATTERN_META,
    SERVICE_LEVEL,
    SERVICE_LEVEL_Z,
    TRADE_AREA,
)
from app.pipeline.types import KnowledgeSignals, ScoreBreakdown

_PEAK_BY_TRADE: dict[str, str] = {
    "office": "주중 점심·퇴근 시간대 수요 집중",
    "residential": "주말·저녁 시간대 수요 집중",
    "campus": "학기 중 낮 시간 고회전, 방학 시 급감",
    "suburban": "주말·차량 유입 시간대 수요 변동",
    "tourist": "휴일·성수기 시즌 피크",
}

_COLD_KEYWORDS = ("냉장", "냉동", "유제품", "간편식", "도시락", "신선")
_DRY_KEYWORDS = ("즉석밥", "라면", "음료", "스낵", "상온", "과자")

# Precise-location POI index contribution to safety Z (documented weight).
FOOT_TRAFFIC_Z_BOOST = 0.35


def _stable_unit(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _product_volatility_boost(product_name: str) -> float:
    name = product_name.lower()
    if any(k in product_name for k in _COLD_KEYWORDS) or any(k in name for k in _COLD_KEYWORDS):
        return 0.35
    if any(k in product_name for k in _DRY_KEYWORDS) or any(k in name for k in _DRY_KEYWORDS):
        return 0.10
    return 0.20


def _normalize_dong(location_dong: str) -> str:
    text = location_dong.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def match_knowledge(
    *,
    location_dong: str,
    product_name: str,
    trade_area: str,
    accessibility: str,
    scores: ScoreBreakdown,
    foot_traffic_index: float = 0.0,
    service_level: str = "sl_95",
) -> KnowledgeSignals:
    dong = _normalize_dong(location_dong)
    # Seed excludes service_level so policy choice only moves Z, not logistics residual.
    seed = f"{dong}|{product_name}|{trade_area}|{accessibility}"
    unit = _stable_unit(seed)
    fti = min(1.0, max(0.0, foot_traffic_index))
    z_policy = SERVICE_LEVEL_Z.get(service_level, SERVICE_LEVEL_Z["sl_95"])
    sl_label = SERVICE_LEVEL.get(service_level, SERVICE_LEVEL["sl_95"])

    # Supply/dong residual only — accessibility is applied once in the engine as risk days.
    # (Lead time itself stays fixed; risk becomes buffer stock, not a new LT.)
    base_delay = scores.supply_difficulty * 0.08
    dong_component = round(unit * 0.45, 2)
    logistics_delay = round(base_delay + dong_component, 2)

    vol_norm = scores.demand_volatility / 5.0
    # Z = service-level policy base + context (volatility / product / POI).
    z_context = (
        vol_norm * 0.45
        + _product_volatility_boost(product_name)
        + unit * 0.15
        + FOOT_TRAFFIC_Z_BOOST * fti
    )
    z_base = z_policy  # policy floor before context
    safety_z = round(z_policy + z_context, 2)

    trade_label = TRADE_AREA[trade_area]
    access_label = ACCESSIBILITY[accessibility]
    peak = _PEAK_BY_TRADE[trade_area]

    # Relative risk indices from deterministic seed — not calibrated probabilities.
    sl_stockout_adj = {"sl_90": 8, "sl_95": 0, "sl_99": -12}.get(service_level, 0)
    stockout_risk_index = int(
        min(
            95,
            max(
                20,
                round(
                    40
                    + scores.demand_volatility * 9
                    + unit * 12
                    + fti * 8
                    + sl_stockout_adj,
                ),
            ),
        ),
    )
    peak_intensity_index = int(
        min(85, max(45, round(48 + scores.demand_volatility * 5 + unit * 10 + fti * 6))),
    )

    # Plain-language notes for store owners (numbers kept; jargon minimized).
    logistics_issue = (
        f"'{dong}'·'{access_label}'이면 배송·하역이 평균보다 "
        f"약 {logistics_delay:.1f}일 더 걸릴 수 있어, 그 분량을 여유 재고로 둡니다."
    )
    if stockout_risk_index >= 70:
        stockout_plain = "바쁠 때 품절 위험이 큰 편"
        stock_action = "여유 재고를 넉넉히 잡습니다"
    elif stockout_risk_index >= 50:
        stockout_plain = "바쁠 때 품절 위험이 있는 편"
        stock_action = "여유 재고를 보통 수준으로 잡습니다"
    else:
        stockout_plain = "품절 위험이 상대적으로 낮은 편"
        stock_action = "여유 재고를 가볍게 잡습니다"
    if peak_intensity_index >= 70:
        peak_plain = "손님이 몰리는 시간대가 뚜렷합니다"
    elif peak_intensity_index >= 55:
        peak_plain = "손님이 몰리는 시간대가 어느 정도 있습니다"
    else:
        peak_plain = "수요가 비교적 고른 편입니다"
    demand_risk = (
        f"'{trade_label}'의 '{product_name}'은 {peak}. {peak_plain}. "
        f"{sl_label} 기준으로는 {stockout_plain}이라 {stock_action}."
    )
    if fti > 0:
        foot_note = (
            f"'{dong}'({trade_label})은 {peak}. "
            f"주변 유동이 있어 여유 재고를 조금 더 높게 잡았습니다."
        )
    else:
        foot_note = (
            f"'{dong}'({trade_label})은 {peak}. "
            f"상권 특성을 반영해 여유 재고 수준을 조정했습니다."
        )
    query = f"{dong} + {product_name} + {trade_label}"

    return KnowledgeSignals(
        logistics_delay_days=logistics_delay,
        safety_z_factor=safety_z,
        safety_z_base=round(z_base, 2),
        service_level_z=z_policy,
        foot_traffic_index=fti,
        foot_traffic_peak_note=foot_note,
        logistics_issue_note=logistics_issue,
        demand_risk_note=demand_risk,
        search_query=query,
    )


def store_safety_stock(
    *,
    safety_z: float,
    lead_time_days: float,
    demand_volatility: int,
    turnover_weight: float,
    daily_demand: float,
    demand_sigma_daily: float | None = None,
) -> float:
    """Statistical safety stock in units (개), demand-proportional.

    Default (L3 proxy when POS sigma unavailable):
      SS = Z * daily_demand * sqrt(LT * vol_norm) * turnover_weight
      vol_norm = demand_volatility / 5 (score 1-5 -> 0.2-1.0).

    Measured (R16, when demand_sigma_daily is set):
      SS = Z * sigma_D * sqrt(LT) * turnover_weight
      (King/ASCM form with daily sigma and performance cycle = LT days).

    Uses fixed contractual LT only; logistics risk is added separately.
    """
    z = max(0.0, float(safety_z))
    lt = max(0.0, float(lead_time_days))
    tw = max(0.0, float(turnover_weight))
    if demand_sigma_daily is not None:
        sigma = max(0.0, float(demand_sigma_daily))
        raw = z * sigma * math.sqrt(lt)
        return round(raw * tw, 2)
    vol_norm = max(0.0, float(demand_volatility)) / 5.0
    inner = max(0.0, lt * vol_norm)
    raw = z * max(0.0, daily_demand) * math.sqrt(inner)
    return round(raw * tw, 2)


def resolve_order_day_pattern(
    *,
    pattern_input: str,
    capa_score: int,
    demand_concentration: int,
) -> tuple[str, bool]:
    """Resolve user pattern (or auto) to a concrete ORDER_PATTERN_META key."""
    if pattern_input != "auto" and pattern_input in ORDER_PATTERN_META:
        return pattern_input, False

    # Auto: tighter CAPA / higher shelf pressure → more frequent weekdays.
    if capa_score <= 1 or demand_concentration >= 5:
        return "mon_wed_fri", True
    if capa_score == 2:
        return "tue_thu", True
    if capa_score == 3:
        return "mon_thu", True
    return "weekly_mon", True


def suggest_order_policy(
    *,
    capa_score: int,
    demand_concentration: int,
    daily_demand: float,
    lead_time_days: float,
    order_day_pattern: str = "auto",
) -> tuple[float, float, str, str, str, bool]:
    """Return order policy levers.

    (cycle_days, order_qty, frequency_label, resolved_pattern, days_label, was_auto)
    """
    _ = lead_time_days  # reserved for future LT-aware cadence caps
    resolved, was_auto = resolve_order_day_pattern(
        pattern_input=order_day_pattern,
        capa_score=capa_score,
        demand_concentration=demand_concentration,
    )
    cycle, days_label, times = ORDER_PATTERN_META[resolved]
    cycle = round(cycle, 2)
    pattern_label = ORDER_DAY_PATTERN.get(resolved, days_label)

    if was_auto:
        freq = f"자동 · {days_label} ({times}회/주)"
    else:
        freq = f"{days_label} ({times}회/주 · 선택 패턴)"

    # Extreme concentration can nudge daily flex even if weekly was chosen manually.
    if demand_concentration >= 5 and resolved == "weekly_mon" and not was_auto:
        freq = f"{freq} — 집중 수요로 주기 단축 검토 권고"
    elif was_auto:
        freq = f"{freq} · {pattern_label}"

    order_qty = max(1.0, round(daily_demand * cycle, 1))
    return cycle, order_qty, freq, resolved, days_label, was_auto
