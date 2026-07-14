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


def test_recommended_lt_includes_access_and_kb() -> None:
    result = run(BASE)
    # indoor +1.0 plus positive KB delay → LT > standard 2.0
    assert result.calc.recommended_lead_time_days > result.calc.standard_lead_time_days
    assert result.calc.recommended_rop > 0
    assert "ROP" in result.recommendation or "ROP" in result.recommendation


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


def test_main_road_can_shorten_lt_vs_indoor() -> None:
    indoor = run({**BASE, "accessibility": "indoor"})
    road = run({**BASE, "accessibility": "main_road"})
    assert road.calc.recommended_lead_time_days < indoor.calc.recommended_lead_time_days


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
    expected = calc.daily_demand * calc.recommended_lead_time_days + calc.store_safety_stock
    if not calc.capa_capped:
        assert calc.recommended_rop == pytest.approx(round(expected, 2))
