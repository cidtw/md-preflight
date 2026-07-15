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

    logistics_issue = (
        f"'{dong}' 인근 배송 이력 패턴과 '{access_label}' 조건을 매칭한 결과, "
        f"상권·행정동 기인 물류 리스크 성분이 약 {logistics_delay:.1f}일로 추정됩니다. "
        f"품목 리드타임 입력값은 유지하고, 이 리스크는 버퍼 재고(개)로 전환합니다. "
        f"(상권 공급 난이도 {scores.supply_difficulty}/5, "
        f"안정 시드 잔차 {dong_component:.2f}일)"
    )
    demand_risk = (
        f"'{trade_label}' 특성과 품목 '{product_name}' 조합에서 {peak} 패턴이 두드러집니다. "
        f"피크 상대 강도 지수 {peak_intensity_index}/100 · 선택 정책 '{sl_label}' 기준 "
        f"표준 ROP 유지 시 피크 품절 상대 위험 점수 {stockout_risk_index}/100"
        f"(모형 추정 인덱스, 실측 확률이 아님)으로 산출되어 "
        f"안전재고·ROP 조정이 필요합니다."
    )
    if fti > 0:
        foot_note = (
            f"{dong} · {trade_label}: {peak}. "
            f"서비스레벨 Z {z_policy:.2f} + 맥락 {z_context:.2f} "
            f"(수요변동 {scores.demand_volatility}/5, 유동지수 {fti:.3f}) "
            f"→ 최종 Z={safety_z:.2f}."
        )
    else:
        foot_note = (
            f"{dong} · {trade_label}: {peak}. "
            f"서비스레벨 Z {z_policy:.2f} + 맥락 {z_context:.2f} "
            f"(수요변동 {scores.demand_volatility}/5) → 최종 Z≈{safety_z:.2f}."
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
) -> float:
    """Statistical safety stock in units (개), demand-proportional.

    SS = Z * daily_demand * sqrt(LT * vol_norm) * turnover_weight
    where vol_norm = demand_volatility / 5 (score 1-5 -> 0.2-1.0).

    Scales with daily demand like logistics buffer (daily * risk_days).
    Uses fixed contractual LT only; logistics risk is added separately.
    """
    vol_norm = max(0.0, float(demand_volatility)) / 5.0
    inner = max(0.0, lead_time_days * vol_norm)
    raw = safety_z * max(0.0, daily_demand) * math.sqrt(inner)
    return round(raw * turnover_weight, 2)


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
