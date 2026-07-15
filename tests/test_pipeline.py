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
    assert calc.store_safety_stock == pytest.approx(
        calc.statistical_safety_stock + calc.logistics_buffer_units,
    )
    assert calc.suggested_order_qty > 0
    assert calc.order_cycle_days > 0
    assert calc.order_frequency_label
    assert "ROP" in result.recommendation
    assert "고정" in result.recommendation


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
    if result.calc.recommended_rop_raw > (result.calc.max_rop_cap or 0):
        assert result.calc.capa_capped is True
        assert result.calc.multi_order_suggestion is not None
        assert result.calc.recommended_rop <= (result.calc.max_rop_cap or 0)


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
    assert any("서비스 레벨" in m for m in metrics)
    assert any("안전재고" in m for m in metrics)
    assert any("발주량" in m for m in metrics)
    assert any("발주 요일" in m for m in metrics)
    assert any("ROP" in m for m in metrics)
    lt_row = next(r for r in result.comparison.rows if "리드타임" in r.metric)
    assert lt_row.delta == 0.0
    assert lt_row.standard_value == lt_row.recommended_value
    assert "미조정" in lt_row.delta_label or "유지" in lt_row.delta_label


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


def test_analyze_formula_rop_identity() -> None:
    validated = validate_parameters(BASE)
    calc = analyze(validated)
    expected = calc.daily_demand * calc.standard_lead_time_days + calc.store_safety_stock
    if not calc.capa_capped:
        assert calc.recommended_rop == pytest.approx(round(expected, 2))
    assert calc.store_safety_stock == pytest.approx(
        calc.statistical_safety_stock + calc.logistics_buffer_units,
    )
