"""Verified demo store profiles for presentation builds.

These are *curated profiles* with fixed parameters and measured walkthrough
numbers (docs/evidence/demo-scope.md). They are NOT live POS/ERP feeds.

General region cascade + Kakao place search remains available for exploratory
/ dummy paths; the demo narrative is pinned to these 1-2 stores.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, Field

from app.pipeline.types import ParameterValue


class VerifiedDemoStore(BaseModel):
    """One store profile allowed as a first-class demo target."""

    id: str
    title: str
    store_label: str
    blurb: str
    highlight: str
    # Honest scope of "verified"
    verification_note: str
    # Expected walkthrough outcomes (document-only; engine still computes live)
    expected: dict[str, ParameterValue] = Field(default_factory=dict)
    parameters: dict[str, ParameterValue]


# Scenario A — CAPA bottleneck (office convenience · indoor · cold)
_STORE_A: Final[VerifiedDemoStore] = VerifiedDemoStore(
    id="verified-a-yeoksam-cvs",
    title="시연 A · 역삼 오피스 편의점",
    store_label="(무인)편의점 · 소형 · 역삼1동 · 건물 내",
    blurb=(
        "검증 프로필: 오피스 상권·건물 내·냉장 간편식. "
        "이론 ROP가 CAPA 상한에 막혀 다회 소량 발주가 드러납니다."
    ),
    highlight="CAPA 캡 · ROP 31.2 · SS 7.2 · 월수금 · Z 1.65→2.38",
    verification_note=(
        "파라미터·발주 체인 실측 검증 완료 (template v1.6+, 행정동 경로). "
        "POS 실측 수요/재고 연동은 아님. 지도 API 없이 고정 프로필로 재현."
    ),
    expected={
        "recommended_rop": 31.2,
        "store_safety_stock": 7.2,
        "suggested_order_qty": 28.0,
        "order_days_label": "월·수·금",
        "capa_capped": True,
        "service_level_z": 1.65,
    },
    parameters={
        "product_name": "냉장 간편식 도시락",
        "store_type": "convenience",
        "store_size": "cv_s",
        "avg_ticket": "t_le_8k",
        "location_dong": "서울시 강남구 역삼1동",
        "use_precise_location": False,
        "store_address": "",
        "consider_temp_foot_traffic": False,
        "consider_competition_saturation": False,
        "trade_area": "office",
        "accessibility": "indoor",
        "daily_demand": 12,
        "standard_lead_time_days": 2,
        "service_level": "sl_95",
        "order_day_pattern": "auto",
    },
)

# Scenario B — no CAPA clamp · main-road buffer zero (residential super · dry)
_STORE_B: Final[VerifiedDemoStore] = VerifiedDemoStore(
    id="verified-b-yeoksam-super",
    title="시연 B · 역삼 주거 슈퍼",
    store_label="일반 슈퍼 · 주거 밀착 · 역삼1동 · 대로변",
    blurb=(
        "검증 프로필: 주거 상권·대로변·상온 라면. "
        "같은 SL 95%여도 CAPA 캡 없이 맥락 SS가 그대로 반영됩니다."
    ),
    highlight="캡 없음 · ROP 37.04 · SS 21.04 · 월목 · buffer 0",
    verification_note=(
        "파라미터·발주 체인 실측 검증 완료 (A 대조군). "
        "POS 실측 아님. 동일 행정동·다른 매장 체급 비교용."
    ),
    expected={
        "recommended_rop": 37.04,
        "store_safety_stock": 21.04,
        "suggested_order_qty": 28.0,
        "order_days_label": "월·목",
        "capa_capped": False,
        "service_level_z": 1.65,
    },
    parameters={
        "product_name": "상온 라면",
        "store_type": "supermarket",
        "store_size": "sm",
        "avg_ticket": "t_8k_15k",
        "location_dong": "서울시 강남구 역삼1동",
        "use_precise_location": False,
        "store_address": "",
        "consider_temp_foot_traffic": False,
        "consider_competition_saturation": False,
        "trade_area": "residential",
        "accessibility": "main_road",
        "daily_demand": 8,
        "standard_lead_time_days": 2,
        "service_level": "sl_95",
        "order_day_pattern": "auto",
    },
)

VERIFIED_DEMO_STORES: Final[tuple[VerifiedDemoStore, ...]] = (_STORE_A, _STORE_B)

_BY_ID: Final[dict[str, VerifiedDemoStore]] = {s.id: s for s in VERIFIED_DEMO_STORES}


def list_verified_demo_stores() -> list[VerifiedDemoStore]:
    return list(VERIFIED_DEMO_STORES)


def get_verified_demo_store(store_id: str) -> VerifiedDemoStore | None:
    return _BY_ID.get(store_id.strip()) if store_id else None
