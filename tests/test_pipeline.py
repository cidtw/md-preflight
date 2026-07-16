from __future__ import annotations

import pytest

from app.core.errors import InputValidationError
from app.pipeline import run
from app.pipeline.analyze.engine import analyze
from app.pipeline.input.template import validate_parameters
from app.pipeline.types import ParameterValue

BASE: dict[str, ParameterValue] = {
    "product_name": "냉장 간편식",
    "store_type": "convenience",
    "store_size": "cv_s",
    "avg_ticket": "t_le_8k",
    "location_dong": "서울시 마포구 서교동",
    "trade_area": "office",
    "accessibility": "indoor",
    "daily_demand": 12,
    "standard_lead_time_days": 2,
    "standard_rop": 15,
}


def test_pipeline_is_deterministic() -> None:
    a = run(BASE)
    b = run(BASE)
    assert a.model_dump() == b.model_dump()


def test_lead_time_is_fixed_and_risk_becomes_buffer() -> None:
    result = run(BASE)
    calc = result.calc
    # LT is contractual/standard — not a recommended delta.
    assert calc.lead_time_fixed is True
    assert calc.recommended_lead_time_days == calc.standard_lead_time_days
    assert calc.lead_time_delta_days == 0.0
    # indoor access + KB logistics → positive risk buffer
    assert calc.logistics_risk_days > 0
    assert calc.logistics_buffer_units == pytest.approx(
        calc.daily_demand * calc.logistics_risk_days,
    )
    if calc.capa_capped:
        # Display SS is effective under CAPA (not raw statistical + buffer).
        assert calc.store_safety_stock == pytest.approx(
            max(
                0.0,
                calc.recommended_rop
                - calc.daily_demand * calc.standard_lead_time_days,
            ),
            abs=0.02,
        )
    else:
        assert calc.store_safety_stock == pytest.approx(
            calc.statistical_safety_stock + calc.logistics_buffer_units,
        )
    assert calc.suggested_order_qty > 0
    assert calc.order_cycle_days > 0
    assert calc.order_frequency_label
    assert "발주" in result.recommendation
    assert "그대로" in result.recommendation


def test_mismatch_guidance_prefers_size_and_ticket() -> None:
    params = {
        **BASE,
        "store_type": "hypermarket",
        "store_size": "cv_xs",
        "avg_ticket": "t_le_8k",
    }
    validated = validate_parameters(params)
    assert len(validated.guidance) >= 2
    assert any("규모" in g for g in validated.guidance)
    assert any("객단가" in g for g in validated.guidance)
    result = run(params)
    assert result.guidance == validated.guidance
    # CAPA for cv_xs is tight → multi-order path more likely
    assert result.calc.scores.capa_score == 1


def test_capa_cap_triggers_multi_order() -> None:
    params: dict[str, ParameterValue] = {
        **BASE,
        "store_size": "cv_xs",
        "daily_demand": 40,
        "standard_lead_time_days": 2,
        "trade_area": "tourist",
        "accessibility": "indoor",
    }
    result = run(params)
    assert result.calc.max_rop_cap is not None
    assert result.calc.recommended_rop_raw > result.calc.max_rop_cap
    assert result.calc.capa_capped is True
    assert result.calc.multi_order_suggestion is not None
    assert result.calc.recommended_rop == pytest.approx(result.calc.max_rop_cap)
    # After CAPA cap, ROP = daily_demand * LT + store_safety_stock must hold.
    expected_ss = result.calc.recommended_rop - (
        result.calc.daily_demand * result.calc.standard_lead_time_days
    )
    assert result.calc.store_safety_stock == pytest.approx(max(0.0, expected_ss), abs=0.02)
    assert result.calc.recommended_rop == pytest.approx(
        result.calc.daily_demand * result.calc.standard_lead_time_days
        + result.calc.store_safety_stock,
        abs=0.02,
    )


def test_main_road_has_lower_logistics_buffer_than_indoor() -> None:
    indoor = run({**BASE, "accessibility": "indoor"})
    road = run({**BASE, "accessibility": "main_road"})
    # Same fixed LT; better access reduces risk buffer and usually ROP.
    assert road.calc.recommended_lead_time_days == indoor.calc.recommended_lead_time_days
    assert road.calc.logistics_risk_days < indoor.calc.logistics_risk_days
    assert road.calc.logistics_buffer_units < indoor.calc.logistics_buffer_units
    assert road.calc.recommended_rop <= indoor.calc.recommended_rop


def test_comparison_includes_operational_levers() -> None:
    result = run(BASE)
    metrics = [row.metric for row in result.comparison.rows]
    assert any("리드타임" in m for m in metrics)
    assert any("품절 방어" in m for m in metrics)
    assert any("여유 재고" in m for m in metrics)
    assert any("발주량" in m for m in metrics)
    assert any("발주 요일" in m for m in metrics)
    assert any("발주 시점" in m for m in metrics)
    lt_row = next(r for r in result.comparison.rows if "리드타임" in r.metric)
    assert lt_row.delta == 0.0
    assert lt_row.standard_value == lt_row.recommended_value
    assert "유지" in lt_row.delta_label or "그대로" in lt_row.delta_label
    z_row = next(r for r in result.comparison.rows if "품절 방어" in r.metric)
    assert z_row.standard_value == pytest.approx(result.calc.knowledge.service_level_z)
    assert z_row.recommended_value == pytest.approx(result.calc.knowledge.safety_z_factor)
    assert z_row.delta == pytest.approx(
        result.calc.knowledge.safety_z_factor - result.calc.knowledge.service_level_z,
    )
    cycle_row = next(r for r in result.comparison.rows if "발주 요일" in r.metric)
    # Auto pattern: standard is weekly 7d, not LT days
    assert cycle_row.standard_value == pytest.approx(7.0)
    assert cycle_row.standard_value != result.calc.standard_lead_time_days


def test_statistical_ss_scales_with_daily_demand() -> None:
    # Roomy CAPA so raw statistical SS is visible (not only CAPA-capped ROP).
    roomy = {
        **BASE,
        "store_type": "ssm",
        "store_size": "ssm",
        "avg_ticket": "t_15k_25k",
        "standard_lead_time_days": 2,
    }
    low = run({**roomy, "daily_demand": 10})
    high = run({**roomy, "daily_demand": 20})
    assert low.calc.statistical_safety_stock > 0
    # Per-call round(..., 2) can introduce 0.01-level drift on exact 2x.
    assert high.calc.statistical_safety_stock == pytest.approx(
        low.calc.statistical_safety_stock * 2,
        abs=0.05,
    )
    assert high.calc.logistics_buffer_units == pytest.approx(
        low.calc.logistics_buffer_units * 2,
        abs=0.05,
    )


def test_size_band_defaults_when_lt_rop_omitted() -> None:
    # hypermarket type + cv_xs size: defaults must follow size (convenience), not type.
    params = {
        "product_name": "냉장 간편식",
        "store_type": "hypermarket",
        "store_size": "cv_xs",
        "avg_ticket": "t_le_8k",
        "location_dong": "서울시 마포구 서교동",
        "trade_area": "office",
        "accessibility": "indoor",
        "daily_demand": 12,
    }
    result = run(params)
    assert result.calc.standard_lead_time_days == pytest.approx(1.5)  # convenience
    assert any("규모" in g for g in result.guidance)


def test_service_level_raises_z_and_rop() -> None:
    # Use roomy CAPA so ROP is not flattened by max-cap.
    roomy = {
        **BASE,
        "store_type": "ssm",
        "store_size": "ssm",
        "avg_ticket": "t_15k_25k",
    }
    low = run({**roomy, "service_level": "sl_90"})
    high = run({**roomy, "service_level": "sl_99"})
    assert high.calc.knowledge.service_level_z > low.calc.knowledge.service_level_z
    assert high.calc.knowledge.safety_z_factor > low.calc.knowledge.safety_z_factor
    assert high.calc.store_safety_stock > low.calc.store_safety_stock
    assert high.calc.recommended_rop > low.calc.recommended_rop
    assert low.calc.capa_capped is False
    assert high.calc.capa_capped is False
    # Comparison standard Z is selected policy, not a hardcoded sl_95 baseline.
    low_z = next(r for r in low.comparison.rows if "품절 방어" in r.metric)
    high_z = next(r for r in high.comparison.rows if "품절 방어" in r.metric)
    assert low_z.standard_value == pytest.approx(1.28)
    assert high_z.standard_value == pytest.approx(2.33)


def test_order_day_pattern_selection() -> None:
    auto = run({**BASE, "order_day_pattern": "auto", "store_size": "cv_xs"})
    fixed = run({**BASE, "order_day_pattern": "tue_thu", "store_size": "cv_xs"})
    assert auto.calc.order_pattern_auto is True
    assert auto.calc.order_day_pattern == "mon_wed_fri"  # tight CAPA auto
    assert "월" in auto.calc.order_days_label
    assert fixed.calc.order_pattern_auto is False
    assert fixed.calc.order_day_pattern == "tue_thu"
    assert "화" in fixed.calc.order_days_label
    assert fixed.calc.order_cycle_days == pytest.approx(3.5)


def test_product_lt_input_is_kept_not_adjusted() -> None:
    result = run({**BASE, "standard_lead_time_days": 3.5})
    assert result.calc.standard_lead_time_days == 3.5
    assert result.calc.recommended_lead_time_days == 3.5
    assert result.calc.lead_time_delta_days == 0.0


def test_missing_required() -> None:
    with pytest.raises(InputValidationError, match="product_name"):
        _ = validate_parameters({"store_type": "convenience"})


def test_unknown_parameter() -> None:
    with pytest.raises(InputValidationError, match="Unknown"):
        _ = validate_parameters({**BASE, "extra": 1})


def test_evidence_is_input_specific_not_fixed_doc_example() -> None:
    result = run({**BASE, "location_dong": "부산시 해운대구 우동", "product_name": "상온 즉석밥"})
    blob = " ".join(p for b in result.evidence for p in b.points)
    assert "해운대구 우동" in blob or "우동" in blob
    assert "즉석밥" in blob
    # Must not hard-copy the design-doc fixed sample narrative anchors.
    assert "역삼1동" not in blob
    assert "240%" not in blob
    assert any(b.id == "geo_poi" for b in result.evidence)
    # Dual narrative: technical path present and distinct.
    assert result.recommendation_technical
    assert result.evidence_technical
    assert result.comparison_technical is not None
    tech_blob = " ".join(p for b in result.evidence_technical for p in b.points)
    assert "Z" in tech_blob or "CAPA" in tech_blob or "sqrt" in tech_blob


def test_analyze_formula_rop_identity() -> None:
    validated = validate_parameters(BASE)
    calc = analyze(validated)
    expected = calc.daily_demand * calc.standard_lead_time_days + calc.store_safety_stock
    # Identity always holds on displayed ROP/SS (CAPA path recomputes effective SS).
    assert calc.recommended_rop == pytest.approx(round(expected, 2), abs=0.02)
    if calc.capa_capped:
        assert calc.recommended_rop == pytest.approx(calc.max_rop_cap)
        assert calc.store_safety_stock < (
            calc.statistical_safety_stock + calc.logistics_buffer_units
        )
    else:
        assert calc.store_safety_stock == pytest.approx(
            calc.statistical_safety_stock + calc.logistics_buffer_units,
        )


def test_ss_comparison_identity_with_custom_standard_rop() -> None:
    """SS standard column must match user standard_rop under ROP = D*LT + SS."""
    # BASE has standard_rop=15, D=12, LT=2 -> demand during LT = 24 > 15 -> std SS = 0
    result = run(BASE)
    d_lt = result.calc.daily_demand * result.calc.standard_lead_time_days
    expected_std_ss = max(0.0, result.calc.standard_rop - d_lt)
    ss_row = next(r for r in result.comparison.rows if "여유 재고" in r.metric)
    assert ss_row.standard_value == pytest.approx(expected_std_ss)
    assert ss_row.standard_value != pytest.approx(result.calc.base_safety_stock)
    # Identity: standard ROP ~ D*LT + standard SS (when standard_rop >= D*LT, exact).
    roomy = {
        **BASE,
        "store_type": "ssm",
        "store_size": "ssm",
        "avg_ticket": "t_15k_25k",
        "standard_rop": 50,
        "daily_demand": 10,
        "standard_lead_time_days": 2,
    }
    roomy_result = run(roomy)
    d_lt_r = roomy_result.calc.daily_demand * roomy_result.calc.standard_lead_time_days
    ss_r = next(r for r in roomy_result.comparison.rows if "여유 재고" in r.metric)
    assert ss_r.standard_value == pytest.approx(50 - d_lt_r)
    assert roomy_result.calc.standard_rop == pytest.approx(
        d_lt_r + ss_r.standard_value,
    )


def test_q_baseline_uses_cycle_not_lt() -> None:
    """Q standard must share the cycle-row baseline, not LT days."""
    # Auto weekly default → std cycle 7d; tight CAPA auto may pick mon_wed_fri.
    # Use roomy size so auto resolves to weekly_mon (7d).
    roomy = {
        **BASE,
        "store_type": "ssm",
        "store_size": "ssm",
        "avg_ticket": "t_15k_25k",
        "order_day_pattern": "auto",
    }
    auto = run(roomy)
    q_row = next(r for r in auto.comparison.rows if "발주량" in r.metric)
    cycle_row = next(r for r in auto.comparison.rows if "발주 요일" in r.metric)
    assert cycle_row.standard_value == pytest.approx(7.0)
    assert q_row.standard_value == pytest.approx(auto.calc.daily_demand * 7.0)
    assert q_row.standard_value != pytest.approx(
        auto.calc.daily_demand * auto.calc.standard_lead_time_days,
    )

    fixed = run({**roomy, "order_day_pattern": "mon_wed_fri"})
    q_fixed = next(r for r in fixed.comparison.rows if "발주량" in r.metric)
    # Fixed pattern: std cycle == rec cycle → Q delta should not invent LT uplift.
    assert q_fixed.standard_value == pytest.approx(fixed.calc.suggested_order_qty)
    assert q_fixed.delta == pytest.approx(0.0)


def test_capa_clamps_order_qty_to_max_rop_cap() -> None:
    """When CAPA sets max ROP, suggested order qty must not exceed that ceiling."""
    # capa 2 (cv_m-ish) + high D + short LT: cycle can exceed cover window.
    # cv_xs → capa 1, auto mon_wed_fri cycle ~2.33d; max cover often < cycle*D for high D.
    params: dict[str, ParameterValue] = {
        **BASE,
        "store_size": "cv_xs",
        "daily_demand": 40,
        "standard_lead_time_days": 2,
        "trade_area": "tourist",
        "accessibility": "indoor",
        "order_day_pattern": "weekly_mon",  # cycle 7d → Q=280, max_rop much smaller
    }
    result = run(params)
    assert result.calc.max_rop_cap is not None
    assert result.calc.suggested_order_qty <= result.calc.max_rop_cap + 1e-9
    # Without clamp, D*7 would exceed max_rop for this setup.
    uncapped_q = result.calc.daily_demand * 7.0
    assert uncapped_q > result.calc.max_rop_cap
    assert result.calc.multi_order_suggestion is not None
    assert "발주량" in result.calc.multi_order_suggestion or "1회" in (
        result.calc.multi_order_suggestion or ""
    )


def test_store_safety_stock_edge_cases() -> None:
    from app.pipeline.analyze.knowledge_base import store_safety_stock

    # vol score 1 → vol_norm 0.2; short LT half-day still yields finite SS.
    low = store_safety_stock(
        safety_z=1.65,
        lead_time_days=0.5,
        demand_volatility=1,
        turnover_weight=1.0,
        daily_demand=10.0,
    )
    assert low > 0
    high_vol = store_safety_stock(
        safety_z=1.65,
        lead_time_days=0.5,
        demand_volatility=5,
        turnover_weight=1.0,
        daily_demand=10.0,
    )
    assert high_vol > low
    zero_d = store_safety_stock(
        safety_z=1.65,
        lead_time_days=2.0,
        demand_volatility=3,
        turnover_weight=1.0,
        daily_demand=0.0,
    )
    assert zero_d == 0.0
