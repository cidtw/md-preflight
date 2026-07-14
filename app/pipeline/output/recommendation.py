"""Stage 3 — ROP comparison dashboard and evidence report."""

from __future__ import annotations

from app.pipeline.domain_catalog import (
    ACCESSIBILITY,
    AVG_TICKET,
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


def _summary(validated: ValidatedInput) -> StoreSummary:
    p = validated.parameters
    use_precise = bool(p.get("use_precise_location", False))
    address = p.get("store_address")
    return StoreSummary(
        product_name=str(p["product_name"]),
        store_type_label=STORE_TYPE[str(p["store_type"])],
        store_size_label=STORE_SIZE[str(p["store_size"])],
        avg_ticket_label=AVG_TICKET[str(p["avg_ticket"])],
        location_dong=str(p["location_dong"]),
        trade_area_label=TRADE_AREA[str(p["trade_area"])],
        accessibility_label=ACCESSIBILITY[str(p["accessibility"])],
        use_precise_location=use_precise,
        store_address=str(address) if address is not None else None,
    )


def _comparison(calc: CalcBreakdown) -> ComparisonDashboard:
    rows = [
        ComparisonRow(
            metric="리드타임 (Lead Time)",
            standard_value=calc.standard_lead_time_days,
            recommended_value=calc.recommended_lead_time_days,
            delta=calc.lead_time_delta_days,
            unit="일",
            delta_label=_delta_label(calc.lead_time_delta_days, higher_is_delay=True),
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
            f"{calc.rop_delta:.0f}개 더 빠르게 발주)"
        )
    elif calc.rop_delta < 0:
        guide = (
            f"매장 재고가 {rop:.0f}개 이하일 때 발주하면 됩니다. "
            f"표준 {std:.0f}개 대비 재고 부담을 {abs(calc.rop_delta):.0f}개 줄인 운영이 가능합니다."
        )
    else:
        guide = f"표준과 동일한 ROP {rop:.0f}개를 유지하는 것이 현재 조건에 부합합니다."
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
    z_delta = calc.knowledge.safety_z_factor - calc.knowledge.safety_z_base
    points.append(
        f"foot_traffic_index={geo.foot_traffic_index:.3f} → "
        + f"안전계수 Z {calc.knowledge.safety_z_base:.2f}에서 "
        + f"{calc.knowledge.safety_z_factor:.2f}로 보정 "
        + f"(+{z_delta:.2f}).",
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
        title="공급망 지연 및 물류 접근성 (Lead Time 조정 근거)",
        calc_summary=(
            f"사내 표준 리드타임({calc.standard_lead_time_days:.1f}일) → "
            f"매장 특화 리드타임({calc.recommended_lead_time_days:.1f}일)"
        ),
        points=[
            (
                f"접근성 '{access}' 가산점 {scores.accessibility_lt_delta_days:+.1f}일이 "
                f"표준 LT에 반영되었습니다."
            ),
            kb.logistics_issue_note,
            (
                f"KB 검색 쿼리: {kb.search_query}. "
                f"공급 난이도 {scores.supply_difficulty}/5 · "
                f"AI 물류 지연 예측 +{kb.logistics_delay_days:.2f}일."
            ),
        ],
    )

    rop_block = EvidenceBlock(
        id="demand_safety",
        title="상권 특성 및 수요 변동성 (안전재고 및 ROP 조정 근거)",
        calc_summary=(
            f"표준 안전재고({calc.base_safety_stock:.1f}개) → "
            f"매장 특화 안전재고({calc.store_safety_stock:.1f}개) · "
            f"회전 가중치 {scores.turnover_weight}"
        ),
        points=[
            kb.foot_traffic_peak_note,
            kb.demand_risk_note,
            (
                f"공식: 안전재고 = Z({kb.safety_z_factor}) * "
                f"sqrt(추천LT {calc.recommended_lead_time_days} * "
                f"수요변동성 {scores.demand_volatility}) * "
                f"회전가중치 {scores.turnover_weight}. "
                f"품목 '{product}', 상권 '{trade}', 행정동 '{dong}' 기준."
            ),
        ],
    )

    if calc.capa_capped and calc.multi_order_suggestion:
        capa_points = [
            calc.multi_order_suggestion,
            (
                f"원시 추천 ROP {calc.recommended_rop_raw:.1f}개 → "
                f"CAPA 상한 {calc.max_rop_cap}개로 고정."
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
    sign_lt = "▲" if calc.lead_time_delta_days >= 0 else "▼"
    sign_rop = "▲" if calc.rop_delta >= 0 else "▼"
    base = (
        f"[{summary.product_name}] 추천 LT {calc.recommended_lead_time_days:.1f}일"
        f"({sign_lt}{abs(calc.lead_time_delta_days):.1f}) · "
        f"ROP {calc.recommended_rop:.0f}개"
        f"({sign_rop}{abs(calc.rop_delta):.0f})"
    )
    if calc.geo.enabled and not calc.geo.used_fallback and calc.geo.foot_traffic_index > 0:
        base += f" · 지도 유동지수 {calc.geo.foot_traffic_index:.2f}"
    if calc.multi_order_suggestion:
        return f"{base}. 협소 CAPA로 다회 소량 발주를 권장합니다."
    return f"{base}. 매장·상권 특화 재조정을 적용하세요."


def render(validated: ValidatedInput, calc: CalcBreakdown) -> RecommendationResult:
    summary = _summary(validated)
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
