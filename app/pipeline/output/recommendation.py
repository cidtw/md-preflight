"""Stage 3 — ROP comparison dashboard and evidence report."""

from __future__ import annotations

from app.pipeline.analyze.knowledge_base import FOOT_TRAFFIC_Z_BOOST
from app.pipeline.domain_catalog import (
    ACCESSIBILITY,
    AVG_TICKET,
    ORDER_DAY_PATTERN,
    ORDER_PATTERN_META,
    SERVICE_LEVEL,
    STORE_SIZE,
    STORE_TYPE,
    TRADE_AREA,
)
from app.pipeline.types import (
    CalcBreakdown,
    ComparisonDashboard,
    ComparisonRow,
    EvidenceBlock,
    RecommendationResult,
    StoreSummary,
    ValidatedInput,
)

_CATEGORY_KO = {
    "transit_rail": "철도·지하철",
    "transit_bus": "버스",
    "landmark": "랜드마크",
    "education": "교육",
    "office": "오피스",
    "retail_anchor": "상업 앵커",
    "convenience": "편의점",
    "other": "기타",
}


def _delta_label(delta: float, *, higher_is_delay: bool = False) -> str:
    if abs(delta) < 1e-9:
        return "변동 없음"
    arrow = "▲" if delta > 0 else "▼"
    if higher_is_delay and delta > 0:
        return f"{arrow} {abs(delta):.1f} 지연 반영"
    if delta > 0:
        return f"{arrow} {abs(delta):.1f} 상향"
    return f"{arrow} {abs(delta):.1f} 하향"


def _summary(validated: ValidatedInput, calc: CalcBreakdown) -> StoreSummary:
    p = validated.parameters
    use_precise = bool(p.get("use_precise_location", False))
    address = p.get("store_address")
    sl_key = str(p.get("service_level", calc.service_level))
    pattern_in = str(p.get("order_day_pattern", calc.order_day_pattern_input))
    pattern_label = ORDER_DAY_PATTERN.get(pattern_in, pattern_in)
    if calc.order_pattern_auto and pattern_in == "auto":
        pattern_label = (
            f"{pattern_label} → {calc.order_days_label} "
            f"({ORDER_DAY_PATTERN.get(calc.order_day_pattern, calc.order_day_pattern)})"
        )
    return StoreSummary(
        product_name=str(p["product_name"]),
        store_type_label=STORE_TYPE[str(p["store_type"])],
        store_size_label=STORE_SIZE[str(p["store_size"])],
        avg_ticket_label=AVG_TICKET[str(p["avg_ticket"])],
        location_dong=str(p["location_dong"]),
        trade_area_label=TRADE_AREA[str(p["trade_area"])],
        accessibility_label=ACCESSIBILITY[str(p["accessibility"])],
        service_level_label=SERVICE_LEVEL.get(sl_key, calc.service_level_label),
        order_day_pattern_label=pattern_label,
        use_precise_location=use_precise,
        store_address=str(address) if address is not None else None,
    )


def _standard_safety_stock(calc: CalcBreakdown) -> float:
    """SS baseline consistent with standard ROP under ROP = D*LT + SS."""
    demand_during_lt = calc.daily_demand * calc.standard_lead_time_days
    return round(max(0.0, calc.standard_rop - demand_during_lt), 2)


def _comparison(calc: CalcBreakdown) -> ComparisonDashboard:
    # LT is fixed (not an adjustable lever). Surface adjustable ops: SS, Q, cycle, ROP.
    # SS baseline follows standard_rop identity (user or model), not channel fraction alone.
    std_ss = _standard_safety_stock(calc)
    rec_ss = calc.store_safety_stock
    ss_delta = round(rec_ss - std_ss, 2)
    # Cycle baseline is not LT: auto compares to weekly (7d); fixed pattern → same cycle.
    rec_cycle = calc.order_cycle_days
    weekly_default = ORDER_PATTERN_META["weekly_mon"][0]
    if calc.order_pattern_auto:
        std_cycle = weekly_default
        cycle_delta = round(rec_cycle - std_cycle, 2)
        cycle_delta_label = (
            f"주 1회 기본 {std_cycle:g}일 → {calc.order_days_label} "
            f"{rec_cycle:g}일 · {calc.order_frequency_label}"
        )
    else:
        std_cycle = rec_cycle
        cycle_delta = 0.0
        cycle_delta_label = (
            f"선택 패턴 {calc.order_days_label} · {calc.order_frequency_label}"
        )
    # Q baseline uses the same cycle days as the cycle row (not LT days).
    std_q = round(calc.daily_demand * std_cycle, 1)
    rec_q = calc.suggested_order_qty
    q_delta = round(rec_q - std_q, 1)

    policy_z = calc.knowledge.service_level_z
    context_z = calc.knowledge.safety_z_factor
    z_delta = round(context_z - policy_z, 2)

    rows = [
        ComparisonRow(
            metric="배송 리드타임 (입력값 · 변경 없음)",
            standard_value=calc.standard_lead_time_days,
            recommended_value=calc.recommended_lead_time_days,
            delta=0.0,
            unit="일",
            delta_label="계약·표준 일정 그대로 유지",
        ),
        ComparisonRow(
            metric="품절 방어 수준 (목표 → 매장 반영)",
            standard_value=policy_z,
            recommended_value=context_z,
            delta=z_delta,
            unit="",
            delta_label=(
                f"{calc.service_level_label} 목표를 이 매장 조건에 맞게 조정"
            ),
        ),
        ComparisonRow(
            metric="여유 재고 (안전재고)",
            standard_value=std_ss,
            recommended_value=rec_ss,
            delta=ss_delta,
            unit="개",
            delta_label=_delta_label(ss_delta),
        ),
        ComparisonRow(
            metric="1회 발주량",
            standard_value=std_q,
            recommended_value=rec_q,
            delta=q_delta,
            unit="개",
            delta_label=_delta_label(q_delta),
        ),
        ComparisonRow(
            metric="발주 요일·주기",
            standard_value=std_cycle,
            recommended_value=rec_cycle,
            delta=cycle_delta,
            unit="일",
            delta_label=cycle_delta_label,
        ),
        ComparisonRow(
            metric="발주 시점 재고 (재발주점)",
            standard_value=calc.standard_rop,
            recommended_value=calc.recommended_rop,
            delta=calc.rop_delta,
            unit="개",
            delta_label=_delta_label(calc.rop_delta),
        ),
    ]
    rop = calc.recommended_rop
    std = calc.standard_rop
    if calc.rop_delta > 0:
        guide = (
            f"핵심: 재고가 {rop:.0f}개 이하로 내려가면 그때 발주하세요. "
            f"(일반 기준 {std:.0f}개보다 {calc.rop_delta:.0f}개 여유 있게 잡는 편입니다.) "
            f"발주는 {calc.order_days_label}, 한 번에 약 {calc.suggested_order_qty:g}개."
        )
    elif calc.rop_delta < 0:
        cut = abs(calc.rop_delta)
        guide = (
            f"핵심: 재고가 {rop:.0f}개 이하일 때 발주하면 됩니다. "
            f"일반 기준보다 {cut:.0f}개 덜 쌓아도 되는 편입니다. "
            f"발주 요일은 {calc.order_days_label}."
        )
    else:
        guide = (
            f"핵심: 일반 기준과 같이 재고 {rop:.0f}개에서 발주하면 됩니다. "
            f"발주는 {calc.order_days_label}, 한 번에 약 {calc.suggested_order_qty:g}개."
        )
    return ComparisonDashboard(rows=rows, rop_guidance=guide)


def _geo_evidence(calc: CalcBreakdown) -> EvidenceBlock:
    geo = calc.geo
    if not geo.enabled:
        return EvidenceBlock(
            id="geo_poi",
            title="매장 위치·주변 손님 흐름",
            calc_summary="핵심: 행정동·상권 정보만으로 판단했습니다",
            points=[
                "상세 주소를 넣지 않아 주변 시설 검색은 하지 않았습니다.",
                "행정동과 상권 유형을 기준으로 수요 변동을 반영했습니다.",
            ],
        )
    if geo.used_fallback:
        return EvidenceBlock(
            id="geo_poi",
            title="매장 위치·주변 손님 흐름",
            calc_summary="핵심: 주소 검색이 되지 않아 행정동 기준으로 계산했습니다",
            points=[
                "입력하신 주소를 지도에서 찾지 못했거나, 지도 연결이 원활하지 않았습니다.",
                "이 경우에도 행정동·상권 정보로 여유 재고를 계산해 두었습니다.",
                "가능하면 도로명 주소(번지 포함)로 다시 시도해 주세요.",
            ],
        )

    top = geo.pois[:5]
    poi_lines = [
        (
            f"{p.name} ({_CATEGORY_KO.get(p.category, p.category)}, "
            f"{p.distance_m:.0f}m)"
        )
        for p in top
    ]
    fti = geo.foot_traffic_index
    fti_boost = round(FOOT_TRAFFIC_Z_BOOST * fti, 2)
    points = [
        (
            f"핵심: 매장 주변 {geo.radius_m}m 안 시설을 보고 "
            f"손님 흐름을 반영했습니다. (유동 기여 +{fti_boost:.2f})"
        ),
    ]
    if poi_lines:
        points.append("근처에 눈에 띄는 곳: " + " · ".join(poi_lines))
    else:
        points.append(f"반경 {geo.radius_m}m 안에서는 참고할 시설이 거의 없었습니다.")
    points.append(
        "유동이 클수록 바쁠 때 품절을 막기 위해 여유 재고를 조금 더 잡습니다.",
    )
    if geo.address_queried:
        points.append(f"조회한 주소: {geo.address_queried}")
    return EvidenceBlock(
        id="geo_poi",
        title="매장 위치·주변 손님 흐름",
        calc_summary=(
            f"핵심: 주변 시설 {len(geo.pois)}곳 반영 · "
            f"손님 흐름 지수 {geo.foot_traffic_index:.2f}"
        ),
        points=points,
    )


def _ss_plain_point(calc: CalcBreakdown) -> str:
    """Owner-friendly safety-stock explanation; numbers without formula jargon."""
    if calc.capa_capped:
        return (
            f"여유 재고는 약 {calc.store_safety_stock:.0f}개로 잡았습니다. "
            f"(창고 공간 한도를 맞춰 조정한 값입니다. "
            f"일 판매 약 {calc.daily_demand:g}개, 배송 {calc.standard_lead_time_days:g}일 기준.)"
        )
    return (
        f"여유 재고는 약 {calc.store_safety_stock:.0f}개입니다. "
        f"배송 지연 대비 {calc.logistics_buffer_units:.0f}개 + "
        f"수요 변동 대비 {calc.statistical_safety_stock:.0f}개를 합친 값입니다. "
        f"(하루 약 {calc.daily_demand:g}개 팔릴 때 기준.)"
    )


def _evidence(validated: ValidatedInput, calc: CalcBreakdown) -> list[EvidenceBlock]:
    p = validated.parameters
    access = ACCESSIBILITY[str(p["accessibility"])]
    trade = TRADE_AREA[str(p["trade_area"])]
    dong = str(p["location_dong"])
    product = str(p["product_name"])
    kb = calc.knowledge

    risk_days = calc.logistics_risk_days
    if risk_days <= 0.2:
        risk_plain = "배송이 비교적 수월한 편"
    elif risk_days <= 0.8:
        risk_plain = "배송·하역에 약간의 여유를 두는 편이 좋음"
    else:
        risk_plain = "배송·하역이 평균보다 더딜 수 있음"

    lt_block = EvidenceBlock(
        id="lt_access",
        title="배송이 늦을 수 있나요?",
        calc_summary=(
            f"핵심: 배송 일정은 {calc.standard_lead_time_days:.0f}일 그대로 · "
            f"대신 여유 재고 +{calc.logistics_buffer_units:.0f}개"
        ),
        points=[
            f"'{access}' 입지라 {risk_plain}.",
            kb.logistics_issue_note,
            (
                "계약 배송 일정은 바꾸지 않고, 늦을 수 있는 만큼만 "
                f"재고로 대비합니다. (하루 {calc.daily_demand:g}개 x "
                f"{risk_days:.1f}일 ~ {calc.logistics_buffer_units:.0f}개)"
            ),
        ],
    )

    std_ss = _standard_safety_stock(calc)
    ss_up = calc.store_safety_stock - std_ss
    if ss_up > 0.5:
        ss_take = (
            f"여유 재고를 일반 기준({std_ss:.0f}개)보다 "
            f"{ss_up:.0f}개 더 잡는 편"
        )
    elif ss_up < -0.5:
        ss_take = (
            f"여유 재고를 일반 기준보다 {abs(ss_up):.0f}개 덜 잡아도 되는 편"
        )
    else:
        ss_take = "여유 재고는 일반 기준과 비슷한 수준"

    rop_block = EvidenceBlock(
        id="demand_safety",
        title="왜 이 재고·발주량인가요?",
        calc_summary=(
            f"핵심: {ss_take} · "
            f"1회 {calc.suggested_order_qty:g}개 · {calc.order_days_label}"
        ),
        points=[
            kb.demand_risk_note,
            kb.foot_traffic_peak_note,
            _ss_plain_point(calc),
            (
                f"실무 정리: 재고 {calc.recommended_rop:.0f}개 이하에서 발주, "
                f"'{calc.order_days_label}'에 약 {calc.suggested_order_qty:g}개. "
                f"({product} · {trade} · {dong})"
            ),
        ],
    )

    if calc.capa_capped and calc.multi_order_suggestion:
        capa_points = [
            calc.multi_order_suggestion,
            (
                f"발주 기준 재고 {calc.recommended_rop:.0f}개, "
                f"여유 재고 약 {calc.store_safety_stock:.0f}개로 맞춰 두었습니다."
            ),
        ]
        capa_summary = "핵심: 창고가 좁아 자주·조금씩 넣는 방식이 맞습니다"
    else:
        capa_points = [
            (
                f"추천 재고({calc.recommended_rop:.0f}개)는 "
                f"이 매장 규모에서 무리 없이 둘 수 있는 수준입니다."
            ),
            f"하루 약 {calc.daily_demand:g}개 판매 기준, 적재 부담은 크지 않습니다.",
        ]
        capa_summary = "핵심: 매장 공간에 무리 없이 맞춰 두었습니다"

    capa_block = EvidenceBlock(
        id="capa_filter",
        title="매장 공간에 맞나요?",
        calc_summary=capa_summary,
        points=capa_points,
    )
    return [lt_block, rop_block, _geo_evidence(calc), capa_block]


def _one_liner(summary: StoreSummary, calc: CalcBreakdown) -> str:
    rop = calc.recommended_rop
    qty = calc.suggested_order_qty
    days = calc.order_days_label
    if calc.multi_order_suggestion:
        return (
            f"[{summary.product_name}] 재고가 {rop:.0f}개 이하면 발주하세요. "
            f"창고가 좁으니 '{days}'에 한 번에 약 {qty:g}개씩 자주 넣는 편이 좋습니다. "
            f"(배송 일정 {calc.standard_lead_time_days:.0f}일은 그대로 둡니다.)"
        )
    if calc.rop_delta > 0:
        why = "이 매장은 일반 기준보다 조금 더 여유 있게"
    elif calc.rop_delta < 0:
        why = "이 매장은 일반 기준보다 조금 더 가볍게"
    else:
        why = "일반 기준과 비슷하게"
    return (
        f"[{summary.product_name}] {why} 운영하세요. "
        f"재고 {rop:.0f}개 이하에서 발주 · '{days}' · 1회 약 {qty:g}개. "
        f"(배송 일정 {calc.standard_lead_time_days:.0f}일은 그대로.)"
    )


def render(validated: ValidatedInput, calc: CalcBreakdown) -> RecommendationResult:
    summary = _summary(validated, calc)
    guidance = list(validated.guidance)
    if calc.geo.enabled and calc.geo.used_fallback:
        guidance.extend(calc.geo.notes)
    return RecommendationResult(
        recommendation=_one_liner(summary, calc),
        template_id=validated.template_id,
        template_version=validated.template_version,
        guidance=guidance,
        summary=summary,
        comparison=_comparison(calc),
        evidence=_evidence(validated, calc),
        calc=calc,
    )
