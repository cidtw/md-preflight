"""Pre-set weight tables from the service flow (logistics CAPA x demand axes)."""

from __future__ import annotations

from app.pipeline.types import ScoreBreakdown

# size_key -> (capa_score, demand_concentration)
_SIZE_SCORES: dict[str, tuple[int, int]] = {
    "cv_xs": (1, 5),
    "cv_s": (1, 5),
    "cv_m": (2, 4),
    "cv_l": (2, 4),
    "sm": (3, 3),
    "ssm": (4, 2),
    "hyper": (5, 1),
}

# ticket_key -> turnover weight
_TICKET_TURNOVER: dict[str, float] = {
    "t_le_8k": 1.5,
    "t_8k_15k": 1.5,
    "t_15k_25k": 1.0,
    "t_45k_55k": 1.0,
    "t_ge_55k": 0.7,
}

# trade_area -> (supply_difficulty, demand_volatility)
_TRADE_SCORES: dict[str, tuple[int, int]] = {
    "office": (3, 4),
    "residential": (2, 2),
    "campus": (3, 5),
    "suburban": (1, 3),
    "tourist": (5, 5),
}

# accessibility -> lead-time day delta
_ACCESS_LT_DELTA: dict[str, float] = {
    "main_road": -0.5,
    "alley": 0.5,
    "indoor": 1.0,
}


def score_store(
    *,
    store_size: str,
    avg_ticket: str,
    trade_area: str,
    accessibility: str,
) -> ScoreBreakdown:
    capa, demand_conc = _SIZE_SCORES[store_size]
    supply_diff, demand_vol = _TRADE_SCORES[trade_area]
    return ScoreBreakdown(
        capa_score=capa,
        demand_concentration=demand_conc,
        turnover_weight=_TICKET_TURNOVER[avg_ticket],
        supply_difficulty=supply_diff,
        demand_volatility=demand_vol,
        accessibility_lt_delta_days=_ACCESS_LT_DELTA[accessibility],
    )


def max_rop_for_capa(*, daily_demand: float, recommended_lt: float, capa_score: int) -> float:
    """Physical stock ceiling used when CAPA is tight (scores 1-2)."""
    # Low CAPA: only a short cover window beyond LT; high CAPA: wider buffer.
    cover_days = {
        1: 0.6,
        2: 1.0,
        3: 2.0,
        4: 3.5,
        5: 5.0,
    }.get(capa_score, 2.0)
    return daily_demand * (recommended_lt + cover_days)
