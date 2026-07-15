"""Canonical option catalogs and Korean labels for the ROP service."""

from __future__ import annotations

from typing import Final

# --- Store type ---
STORE_TYPE: Final[dict[str, str]] = {
    "convenience": "(무인)편의점",
    "supermarket": "일반 슈퍼마켓",
    "ssm": "기업형 슈퍼마켓",
    "hypermarket": "대형마트 및 할인점",
}

# --- Floor-area size bands ---
STORE_SIZE: Final[dict[str, str]] = {
    "cv_xs": "편의점-초소형 (가판대~50㎡ 이하)",
    "cv_s": "편의점-소형 (50㎡ 이상~65㎡ 미만)",
    "cv_m": "편의점-중형 (65㎡ 이상~85㎡ 이하)",
    "cv_l": "편의점-대형 (85㎡ 이상~165㎡ 미만)",
    "sm": "일반 슈퍼마켓 (165㎡ 이상~1000㎡ 미만)",
    "ssm": "기업형 슈퍼마켓 (1000㎡ 이상~3000㎡ 미만)",
    "hyper": "대형마트 및 할인점 (3000㎡ 이상)",
}

# Expected size keys per store type (for mismatch guidance).
STORE_TYPE_SIZE_EXPECT: Final[dict[str, frozenset[str]]] = {
    "convenience": frozenset({"cv_xs", "cv_s", "cv_m", "cv_l"}),
    "supermarket": frozenset({"sm"}),
    "ssm": frozenset({"ssm"}),
    "hypermarket": frozenset({"hyper"}),
}

# --- Average ticket (객단가) ---
AVG_TICKET: Final[dict[str, str]] = {
    "t_le_8k": "8,000원 이하 (편의점)",
    "t_8k_15k": "8,000원~15,000원 (일반 슈퍼마켓)",
    "t_15k_25k": "15,000원~25,000원 (기업형 슈퍼마켓)",
    "t_45k_55k": "45,000원~55,000원 (대형마트 및 할인점)",
    "t_ge_55k": "55,000원 이상 (특수할인점)",
}

STORE_TYPE_TICKET_EXPECT: Final[dict[str, frozenset[str]]] = {
    "convenience": frozenset({"t_le_8k"}),
    "supermarket": frozenset({"t_8k_15k"}),
    "ssm": frozenset({"t_15k_25k"}),
    "hypermarket": frozenset({"t_45k_55k", "t_ge_55k"}),
}

# --- Trade area ---
TRADE_AREA: Final[dict[str, str]] = {
    "office": "오피스 및 가로상권",
    "residential": "주거지 밀착상권",
    "campus": "대학가 및 학원가 상권",
    "suburban": "교외 및 대로변 상권",
    "tourist": "복합쇼핑몰 및 관광지",
}

# --- Front accessibility ---
ACCESSIBILITY: Final[dict[str, str]] = {
    "main_road": "대로변 (왕복 2차로 이상)",
    "alley": "이면도로 (골목길)",
    "indoor": "건물 내 입지",
}

# --- Service level (fill-rate policy → base Z from normal approx) ---
SERVICE_LEVEL: Final[dict[str, str]] = {
    "sl_90": "서비스 레벨 90% (재고 부담↓ · 품절 허용↑)",
    "sl_95": "서비스 레벨 95% (표준 균형)",
    "sl_99": "서비스 레벨 99% (품절 최소화 · 안전재고↑)",
}

# Standard normal z for cycle service level targets.
SERVICE_LEVEL_Z: Final[dict[str, float]] = {
    "sl_90": 1.28,
    "sl_95": 1.65,
    "sl_99": 2.33,
}

# --- Order weekday pattern (operator lever; LT stays fixed) ---
ORDER_DAY_PATTERN: Final[dict[str, str]] = {
    "auto": "자동 추천 (CAPA·수요집중 기준)",
    "mon_wed_fri": "월·수·금 (주 3회)",
    "tue_thu": "화·목 (주 2회)",
    "mon_thu": "월·목 (주 2회)",
    "weekly_mon": "주 1회 (월요일)",
    "daily_flex": "매일·수시 (고회전)",
}

# pattern_key -> (cycle_days, weekday labels, times_per_week hint)
ORDER_PATTERN_META: Final[dict[str, tuple[float, str, int]]] = {
    "mon_wed_fri": (2.33, "월·수·금", 3),
    "tue_thu": (3.5, "화·목", 2),
    "mon_thu": (3.5, "월·목", 2),
    "weekly_mon": (7.0, "월요일", 1),
    "daily_flex": (1.0, "매일·수시", 6),
}

# Default channel baselines when user omits standard LT (days).
# LT differs by product/channel — always an input, never a recommended change.
DEFAULT_STANDARD_LT: Final[dict[str, float]] = {
    "convenience": 1.5,
    "supermarket": 2.0,
    "ssm": 2.5,
    "hypermarket": 3.0,
}

# Base safety stock as fraction of (daily * standard LT).
DEFAULT_BASE_SAFETY_FRAC: Final[dict[str, float]] = {
    "convenience": 0.25,
    "supermarket": 0.35,
    "ssm": 0.45,
    "hypermarket": 0.55,
}

# Map floor-area size band → channel key for omitted LT / base-SS defaults.
# Prefer size over store_type when they conflict (AGENTS / scoring already size-first).
SIZE_TO_CHANNEL: Final[dict[str, str]] = {
    "cv_xs": "convenience",
    "cv_s": "convenience",
    "cv_m": "convenience",
    "cv_l": "convenience",
    "sm": "supermarket",
    "ssm": "ssm",
    "hyper": "hypermarket",
}
