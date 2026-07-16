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
    KnowledgeSignals,
    RecommendationResult,
    ScoreBreakdown,
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
            metric="리드타임 (품목 입력 · 변동 추천 없음)",
            standard_value=calc.standard_lead_time_days,
            recommended_value=calc.recommended_lead_time_days,
            delta=0.0,
            unit="일",
            delta_label="입력 유지 · 출력에서 LT 미조정",
        ),
        ComparisonRow(
            metric="서비스 레벨 Z",
            standard_value=policy_z,
            recommended_value=context_z,
            delta=z_delta,
            unit="",
            delta_label=(
                f"{calc.service_level_label} · 정책 Z {policy_z:.2f} → "
                f"맥락 반영 최종 {context_z:.2f}"
            ),
        ),
        ComparisonRow(
            metric="안전재고 (Safety Stock)",
            standard_value=std_ss,
            recommended_value=rec_ss,
            delta=ss_delta,
            unit="개",
            delta_label=_delta_label(ss_delta),
        ),
        ComparisonRow(
            metric="권장 1회 발주량 (Q)",
            standard_value=std_q,
            recommended_value=rec_q,
            delta=q_delta,
            unit="개",
            delta_label=_delta_label(q_delta),
        ),
        ComparisonRow(
            metric="권장 발주 요일·주기",
            standard_value=std_cycle,
            recommended_value=rec_cycle,
            delta=cycle_delta,
            unit="일",
            delta_label=cycle_delta_label,
        ),
        ComparisonRow(
            metric="재발주점 (ROP)",
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
            f"매장 재고가 {rop:.0f}개 이하로 떨어지는 순간 발주를 넣어야 "
            f"품절 없이 공급이 가능합니다. (표준 {std:.0f}개 대비 "
            f"{calc.rop_delta:.0f}개 더 빠르게 발주) · "
            f"발주 요일 {calc.order_days_label}, 1회 약 {calc.suggested_order_qty:g}개."
        )
    elif calc.rop_delta < 0:
        cut = abs(calc.rop_delta)
        guide = (
            f"매장 재고가 {rop:.0f}개 이하일 때 발주하면 됩니다. "
            f"표준 {std:.0f}개 대비 재고 부담을 {cut:.0f}개 줄일 수 있습니다. · "
            f"발주 요일 {calc.order_days_label}."
        )
    else:
        guide = (
            f"표준과 동일한 ROP {rop:.0f}개를 유지하는 것이 현재 조건에 부합합니다. · "
            f"발주 요일 {calc.order_days_label}, 1회 약 {calc.suggested_order_qty:g}개."
        )
    return ComparisonDashboard(rows=rows, rop_guidance=guide)


def _geo_evidence(calc: CalcBreakdown) -> EvidenceBlock:
    geo = calc.geo
    if not geo.enabled:
        return EvidenceBlock(
            id="geo_poi",
            title="정확한 위치 · 주변 유동 유발 요소",
            calc_summary="정확한 위치 미사용 (행정동·상권 점수만 적용)",
            points=list(geo.notes)
            or ["행정동 단위 입지만으로 수요 변동성을 산출했습니다."],
        )
    if geo.used_fallback:
        return EvidenceBlock(
            id="geo_poi",
            title="정확한 위치 · 주변 유동 유발 요소",
            calc_summary=(
                f"정확한 위치 요청됨 · fallback · foot_traffic_index={geo.foot_traffic_index:.3f}"
            ),
            points=[
                *geo.notes,
                "지도 API 보강에 실패하거나 키가 없어 행정동 경로로 안전재고를 계산했습니다.",
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
    points = list(geo.notes)
    if poi_lines:
        points.append("상위 유동 유발 요소: " + " · ".join(poi_lines))
    else:
        points.append(f"반경 {geo.radius_m}m 내 분류 가능한 POI가 거의 없었습니다.")
    fti = geo.foot_traffic_index
    fti_boost = round(FOOT_TRAFFIC_Z_BOOST * fti, 2)
    kb = calc.knowledge
    points.append(
        f"foot_traffic_index={fti:.3f} → 안전계수 Z에 유동 기여 "
        + f"+{fti_boost:.2f} (가중 {FOOT_TRAFFIC_Z_BOOST}). "
        + f"정책 Z {kb.service_level_z:.2f} + 맥락(수요·품목·시드·유동) → "
        + f"최종 {kb.safety_z_factor:.2f}.",
    )
    if geo.address_queried:
        points.append(f"조회 주소: {geo.address_queried}")
    return EvidenceBlock(
        id="geo_poi",
        title="정확한 위치 · 주변 유동 유발 요소 (Kakao Local)",
        calc_summary=(
            f"반경 {geo.radius_m}m · POI {len(geo.pois)}곳 · "
            f"유동지수 {geo.foot_traffic_index:.3f}"
        ),
        points=points,
    )


def _ss_formula_point(
    calc: CalcBreakdown,
    scores: ScoreBreakdown,
    kb: KnowledgeSignals,
) -> str:
    """Safety-stock formula narrative; CAPA path uses effective SS for identity."""
    head = (
        f"서비스 레벨 정책 Z={kb.service_level_z:.2f} "
        f"({calc.service_level_label}) → 맥락 반영 최종 Z={kb.safety_z_factor:.2f}. "
        f"통계 안전재고(캡 전) = Z * 일평균소진 {calc.daily_demand:g} * "
        f"sqrt(입력LT {calc.standard_lead_time_days} * "
        f"vol_norm {scores.demand_volatility}/5) * 회전가중 "
        f"{scores.turnover_weight} = {calc.statistical_safety_stock:.1f}개. "
    )
    if calc.capa_capped:
        pre_cap = calc.statistical_safety_stock + calc.logistics_buffer_units
        tail = (
            f"CAPA 캡 반영 표시 안전재고 = {calc.store_safety_stock:.1f}개 "
            f"(캡 전 통계+버퍼 {pre_cap:.1f}개)."
        )
    else:
        tail = (
            f"총 안전재고 = 통계 + 물류버퍼 "
            f"{calc.logistics_buffer_units:.1f} = {calc.store_safety_stock:.1f}개."
        )
    return head + tail


def _evidence(validated: ValidatedInput, calc: CalcBreakdown) -> list[EvidenceBlock]:
    p = validated.parameters
    access = ACCESSIBILITY[str(p["accessibility"])]
    trade = TRADE_AREA[str(p["trade_area"])]
    dong = str(p["location_dong"])
    product = str(p["product_name"])
    scores = calc.scores
    kb = calc.knowledge

    lt_block = EvidenceBlock(
        id="lt_access",
        title="물류 리스크 → 버퍼 재고 (리드타임은 고정)",
        calc_summary=(
            f"적용 LT {calc.standard_lead_time_days:.1f}일(고정) · "
            f"물류 리스크 {calc.logistics_risk_days:.2f}일 → "
            f"버퍼 {calc.logistics_buffer_units:.1f}개"
        ),
        points=[
            (
                "리드타임은 계약·표준 일정으로 두며 재조정 대상이 아닙니다. "
                "접근성·상권 물류 리스크는 재고 버퍼로만 반영합니다."
            ),
            (
                f"접근성 '{access}' 리스크 성분 {scores.accessibility_lt_delta_days:+.1f}일 "
                f"+ KB 상권·행정동 리스크 +{kb.logistics_delay_days:.2f}일 "
                f"= 합산 리스크 {calc.logistics_risk_days:.2f}일 "
                f"(음수는 0으로 절사)."
            ),
            kb.logistics_issue_note,
            (
                f"버퍼 환산: 일평균 소진 {calc.daily_demand:g} * 리스크 "
                f"{calc.logistics_risk_days:.2f}일 = {calc.logistics_buffer_units:.1f}개. "
                f"KB 검색: {kb.search_query}."
            ),
        ],
    )

    std_ss = _standard_safety_stock(calc)
    rop_block = EvidenceBlock(
        id="demand_safety",
        title="상권 특성 및 운영 레버 (안전재고 · 발주량 · ROP)",
        calc_summary=(
            f"표준 안전재고({std_ss:.1f}개) → "
            f"매장 특화({calc.store_safety_stock:.1f}개) · "
            f"1회 발주 {calc.suggested_order_qty:g}개 / "
            f"주기 {calc.order_cycle_days:g}일"
        ),
        points=[
            kb.foot_traffic_peak_note,
            kb.demand_risk_note,
            _ss_formula_point(calc, scores, kb),
            (
                f"ROP = 일평균소진 {calc.daily_demand:g} * 입력LT "
                f"{calc.standard_lead_time_days:g} + 표시 안전재고 "
                f"{calc.store_safety_stock:.1f}. "
                f"발주 요일 패턴: {calc.order_days_label} "
                f"({'자동' if calc.order_pattern_auto else '선택'}) · "
                f"{calc.order_frequency_label} · 1회 약 {calc.suggested_order_qty:g}개. "
                f"품목 '{product}', 상권 '{trade}', 행정동 '{dong}'."
            ),
        ],
    )

    if calc.capa_capped and calc.multi_order_suggestion:
        capa_points = [
            calc.multi_order_suggestion,
            (
                f"원시 추천 ROP {calc.recommended_rop_raw:.1f}개 → "
                f"CAPA 상한 {calc.max_rop_cap}개로 고정. "
                f"표시 안전재고 {calc.store_safety_stock:.1f}개는 캡 반영 유효값"
                f"(ROP = 일소진*LT + SS 항등 유지)."
            ),
        ]
        capa_summary = "수용 한도 초과 → 다회 소량 발주 전환"
    else:
        capa_points = [
            (
                f"추천 ROP {calc.recommended_rop:.1f}개는 CAPA 점수 "
                f"{scores.capa_score}/5 범위에서 수용 가능으로 판정되었습니다."
            ),
            (
                f"수요 집중도 점수 {scores.demand_concentration}/5 · "
                f"일평균 소진 {calc.daily_demand:g}개 기준 적재 리스크 낮음."
            ),
        ]
        capa_summary = "수용 가능 확인 (안전)"

    capa_block = EvidenceBlock(
        id="capa_filter",
        title="매장 규모(CAPA)에 따른 운영 제약 필터링",
        calc_summary=capa_summary,
        points=capa_points,
    )
    return [lt_block, rop_block, _geo_evidence(calc), capa_block]


def _one_liner(summary: StoreSummary, calc: CalcBreakdown) -> str:
    std_ss = _standard_safety_stock(calc)
    ss_delta = calc.store_safety_stock - std_ss
    sign_rop = "▲" if calc.rop_delta >= 0 else "▼"
    sign_ss = "▲" if ss_delta >= 0 else "▼"
    base = (
        f"[{summary.product_name}] LT {calc.standard_lead_time_days:.1f}일(입력 유지) · "
        f"ROP {calc.recommended_rop:.0f}개"
        f"({sign_rop}{abs(calc.rop_delta):.0f}) · "
        f"안전재고 {calc.store_safety_stock:.0f}개"
        f"({sign_ss}{abs(ss_delta):.0f}) · "
        f"발주 {calc.order_days_label} · 1회 {calc.suggested_order_qty:g}개 · "
        f"SL {calc.knowledge.service_level_z:.2f}→Z {calc.knowledge.safety_z_factor:.2f}"
    )
    if calc.geo.enabled and not calc.geo.used_fallback and calc.geo.foot_traffic_index > 0:
        base += f" · 지도 유동지수 {calc.geo.foot_traffic_index:.2f}"
    if calc.multi_order_suggestion:
        return f"{base}. 협소 CAPA로 상한 고정·다회 소량 발주를 권장합니다."
    return f"{base}. 조정 레버는 ROP·안전재고·발주 요일/량·서비스 레벨입니다."


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
