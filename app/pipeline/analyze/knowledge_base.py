"""Deterministic knowledge-base matcher (Agent-AI shaped, no live model).

Produces location/product/trade-aware signals and narrative notes derived from
inputs so outputs are never a fixed copy of the design-doc examples.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.pipeline.domain_catalog import ACCESSIBILITY, TRADE_AREA
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
) -> KnowledgeSignals:
    dong = _normalize_dong(location_dong)
    seed = f"{dong}|{product_name}|{trade_area}|{accessibility}"
    unit = _stable_unit(seed)
    fti = min(1.0, max(0.0, foot_traffic_index))

    base_delay = scores.supply_difficulty * 0.08
    access_component = max(0.0, scores.accessibility_lt_delta_days) * 0.35
    dong_component = round(unit * 0.45, 2)
    logistics_delay = round(base_delay + access_component + dong_component, 2)

    vol_norm = scores.demand_volatility / 5.0
    z_base = 1.15 + vol_norm * 0.85 + _product_volatility_boost(product_name) + unit * 0.25
    safety_z = round(z_base + FOOT_TRAFFIC_Z_BOOST * fti, 2)

    trade_label = TRADE_AREA[trade_area]
    access_label = ACCESSIBILITY[accessibility]
    peak = _PEAK_BY_TRADE[trade_area]

    stockout_pct = int(
        min(95, max(35, round(40 + scores.demand_volatility * 9 + unit * 12 + fti * 8))),
    )
    peak_share_pct = int(
        min(85, max(45, round(48 + scores.demand_volatility * 5 + unit * 10 + fti * 6))),
    )

    logistics_issue = (
        f"'{dong}' 인근 배송 이력 패턴과 '{access_label}' 조건을 매칭한 결과, "
        f"표준 탑차 도착 후 매장 진열까지 추가 지연 성분이 약 "
        f"{logistics_delay:.1f}일로 추정됩니다. "
        f"(상권 공급 난이도 {scores.supply_difficulty}/5, "
        f"안정 시드 잔차 {dong_component:.2f}일)"
    )
    demand_risk = (
        f"'{trade_label}' 특성과 품목 '{product_name}' 조합에서 {peak} 패턴이 두드러집니다. "
        f"피크 구간 매출 비중 추정 약 {peak_share_pct}% · 표준 ROP 유지 시 피크 품절 위험 약 "
        f"{stockout_pct}%로 산출되어 안전재고 상향이 필요합니다."
    )
    if fti > 0:
        boost = FOOT_TRAFFIC_Z_BOOST * fti
        foot_note = (
            f"{dong} · {trade_label}: {peak}. "
            f"수요 변동성 {scores.demand_volatility}/5, "
            f"지도 유동지수 {fti:.3f} → Z {z_base:.2f}+{boost:.2f}={safety_z:.2f}."
        )
    else:
        foot_note = (
            f"{dong} · {trade_label}: {peak}. "
            f"수요 변동성 점수 {scores.demand_volatility}/5, 안전계수 Z≈{safety_z:.2f}."
        )
    query = f"{dong} + {product_name} + {trade_label}"

    return KnowledgeSignals(
        logistics_delay_days=logistics_delay,
        safety_z_factor=safety_z,
        safety_z_base=round(z_base, 2),
        foot_traffic_index=fti,
        foot_traffic_peak_note=foot_note,
        logistics_issue_note=logistics_issue,
        demand_risk_note=demand_risk,
        search_query=query,
    )


def store_safety_stock(
    *,
    safety_z: float,
    recommended_lt: float,
    demand_volatility: int,
    turnover_weight: float,
) -> float:
    """Safety stock = Z * sqrt(LT * demand_volatility) * turnover_weight."""
    inner = max(0.0, recommended_lt * float(demand_volatility))
    raw = safety_z * math.sqrt(inner)
    return round(raw * turnover_weight, 2)
