"""Stage 3 — ROP comparison dashboard and evidence report.

Produces dual narratives:
  - plain (default): store-owner friendly
  - technical: specialist formulas / Z / CAPA / FTI jargon
"""

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


def _cycle_baseline(calc: CalcBreakdown) -> tuple[float, float, str]:
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
    return std_cycle, cycle_delta, cycle_delta_label


def _comparison_values(calc: CalcBreakdown) -> dict[str, float]:
    std_ss = _standard_safety_stock(calc)
    std_cycle, cycle_delta, _ = _cycle_baseline(calc)
    std_q = round(calc.daily_demand * std_cycle, 1)
    return {
        "std_ss": std_ss,
        "rec_ss": calc.store_safety_stock,
        "ss_delta": round(calc.store_safety_stock - std_ss, 2),
        "std_cycle": std_cycle,
        "rec_cycle": calc.order_cycle_days,
        "cycle_delta": cycle_delta,
        "std_q": std_q,
        "rec_q": calc.suggested_order_qty,
        "q_delta": round(calc.suggested_order_qty - std_q, 1),
        "policy_z": calc.knowledge.service_level_z,
        "context_z": calc.knowledge.safety_z_factor,
        "z_delta": round(
            calc.knowledge.safety_z_factor - calc.knowledge.service_level_z,
            2,
        ),
    }


def _comparison_plain(calc: CalcBreakdown) -> ComparisonDashboard:
    v = _comparison_values(calc)
    _, _, cycle_delta_label = _cycle_baseline(calc)
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
            standard_value=v["policy_z"],
            recommended_value=v["context_z"],
            delta=v["z_delta"],
            unit="",
            delta_label=f"{calc.service_level_label} 목표를 이 매장 조건에 맞게 조정",
        ),
        ComparisonRow(
            metric="여유 재고 (안전재고)",
            standard_value=v["std_ss"],
            recommended_value=v["rec_ss"],
            delta=v["ss_delta"],
            unit="개",
            delta_label=_delta_label(v["ss_delta"]),
        ),
        ComparisonRow(
            metric="1회 발주량",
            standard_value=v["std_q"],
            recommended_value=v["rec_q"],
            delta=v["q_delta"],
            unit="개",
            delta_label=_delta_label(v["q_delta"]),
        ),
        ComparisonRow(
            metric="발주 요일·주기",
            standard_value=v["std_cycle"],
            recommended_value=v["rec_cycle"],
            delta=v["cycle_delta"],
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


def _comparison_technical(calc: CalcBreakdown) -> ComparisonDashboard:
    v = _comparison_values(calc)
    _, _, cycle_delta_label = _cycle_baseline(calc)
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
            standard_value=v["policy_z"],
            recommended_value=v["context_z"],
            delta=v["z_delta"],
            unit="",
            delta_label=(
                f"{calc.service_level_label} · 정책 Z {v['policy_z']:.2f} → "
                f"맥락 반영 최종 {v['context_z']:.2f}"
            ),
        ),
        ComparisonRow(
            metric="안전재고 (Safety Stock)",
            standard_value=v["std_ss"],
            recommended_value=v["rec_ss"],
            delta=v["ss_delta"],
            unit="개",
            delta_label=_delta_label(v["ss_delta"]),
        ),
        ComparisonRow(
            metric="권장 1회 발주량 (Q)",
            standard_value=v["std_q"],
            recommended_value=v["rec_q"],
            delta=v["q_delta"],
            unit="개",
            delta_label=_delta_label(v["q_delta"]),
        ),
        ComparisonRow(
            metric="권장 발주 요일·주기",
            standard_value=v["std_cycle"],
            recommended_value=v["rec_cycle"],
            delta=v["cycle_delta"],
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
            f"ROP {rop:.0f}개 이하 시 발주 권고 "
            f"(표준 {std:.0f} · Δ{calc.rop_delta:.0f}). "
            f"pattern={calc.order_day_pattern} · Q≈{calc.suggested_order_qty:g}."
        )
    elif calc.rop_delta < 0:
        guide = (
            f"ROP {rop:.0f}개 이하 시 발주 (표준 대비 -{abs(calc.rop_delta):.0f}). "
            f"pattern={calc.order_day_pattern}."
        )
    else:
        guide = (
            f"표준 ROP {rop:.0f}개 유지. "
            f"pattern={calc.order_day_pattern} · Q≈{calc.suggested_order_qty:g}."
        )
    return ComparisonDashboard(rows=rows, rop_guidance=guide)


def _geo_plain(calc: CalcBreakdown) -> EvidenceBlock:
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
        f"{p.name} ({_CATEGORY_KO.get(p.category, p.category)}, {p.distance_m:.0f}m)"
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


def _geo_technical(calc: CalcBreakdown) -> EvidenceBlock:
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
                f"정확한 위치 요청됨 · fallback · "
                f"foot_traffic_index={geo.foot_traffic_index:.3f}"
            ),
            points=[
                *geo.notes,
                "지도 API 보강에 실패하거나 키가 없어 행정동 경로로 안전재고를 계산했습니다.",
            ],
        )
    top = geo.pois[:5]
    poi_lines = [
        f"{p.name} ({_CATEGORY_KO.get(p.category, p.category)}, {p.distance_m:.0f}m)"
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


def _ss_plain_point(calc: CalcBreakdown) -> str:
    if calc.capa_capped:
        return (
            f"여유 재고는 약 {calc.store_safety_stock:.0f}개로 잡았습니다. "
            f"(창고 공간 한도를 맞춰 조정한 값입니다. "
            f"일 판매 약 {calc.daily_demand:g}개, 배송 "
            f"{calc.standard_lead_time_days:g}일 기준.)"
        )
    return (
        f"여유 재고는 약 {calc.store_safety_stock:.0f}개입니다. "
        f"배송 지연 대비 {calc.logistics_buffer_units:.0f}개 + "
        f"수요 변동 대비 {calc.statistical_safety_stock:.0f}개를 합친 값입니다. "
        f"(하루 약 {calc.daily_demand:g}개 팔릴 때 기준.)"
    )


def _ss_formula_technical(
    calc: CalcBreakdown,
    scores: ScoreBreakdown,
) -> str:
    kb = calc.knowledge
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


def _evidence_plain(validated: ValidatedInput, calc: CalcBreakdown) -> list[EvidenceBlock]:
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
            f"여유 재고를 일반 기준({std_ss:.0f}개)보다 {ss_up:.0f}개 더 잡는 편"
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

    # Q-only clamp also sets multi_order_suggestion (ROP may still fit MaxCap).
    if calc.multi_order_suggestion:
        capa_points = [
            calc.multi_order_suggestion,
            (
                f"발주 기준 재고 {calc.recommended_rop:.0f}개, "
                f"여유 재고 약 {calc.store_safety_stock:.0f}개, "
                f"1회 발주 약 {calc.suggested_order_qty:g}개로 맞춰 두었습니다."
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
    return [lt_block, rop_block, _geo_plain(calc), capa_block]


def _evidence_technical(
    validated: ValidatedInput,
    calc: CalcBreakdown,
) -> list[EvidenceBlock]:
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
                f"접근성 '{access}' 리스크 성분 "
                f"{scores.accessibility_lt_delta_days:+.1f}일 "
                f"+ KB 상권·행정동 리스크 +{kb.logistics_delay_days:.2f}일 "
                f"= 합산 리스크 {calc.logistics_risk_days:.2f}일 "
                f"(음수는 0으로 절사)."
            ),
            (
                f"'{dong}' 인근 배송 이력 패턴과 '{access}' 조건을 매칭. "
                f"상권 공급 난이도 {scores.supply_difficulty}/5 · "
                f"KB logistics_delay={kb.logistics_delay_days:.2f}일."
            ),
            (
                f"버퍼 환산: 일평균 소진 {calc.daily_demand:g} * 리스크 "
                f"{calc.logistics_risk_days:.2f}일 = "
                f"{calc.logistics_buffer_units:.1f}개. "
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
            (
                f"{dong} · {trade}: Z_policy={kb.service_level_z:.2f} → "
                f"Z={kb.safety_z_factor:.2f} "
                f"(vol={scores.demand_volatility}/5, "
                f"fti={kb.foot_traffic_index:.3f})."
            ),
            (
                f"수요 위험: 품목 '{product}' · 상권 '{trade}' · "
                f"turnover_weight={scores.turnover_weight}."
            ),
            _ss_formula_technical(calc, scores),
            (
                f"ROP = D {calc.daily_demand:g} * LT "
                f"{calc.standard_lead_time_days:g} + SS "
                f"{calc.store_safety_stock:.1f}. "
                f"pattern={calc.order_day_pattern} "
                f"({'auto' if calc.order_pattern_auto else 'fixed'}) · "
                f"{calc.order_frequency_label} · Q≈{calc.suggested_order_qty:g}."
            ),
        ],
    )

    if calc.multi_order_suggestion:
        if calc.capa_capped:
            capa_points = [
                (
                    f"CAPA 점수 {scores.capa_score}/5(협소): raw ROP "
                    f"{calc.recommended_rop_raw:.1f} → MaxCap "
                    f"{calc.max_rop_cap} 고정. "
                    f"effective SS={calc.store_safety_stock:.1f} "
                    f"(항등 ROP=D*LT+SS 유지)."
                ),
                (
                    f"Q={calc.suggested_order_qty:g} "
                    f"(cycle={calc.order_cycle_days:g}d · {calc.order_days_label}). "
                    f"다회 소량 발주 경로 활성."
                ),
            ]
            capa_summary = "수용 한도 초과 → 다회 소량 발주 전환"
        else:
            # ROP fits MaxCap but Q was reduced to the stock ceiling.
            capa_points = [
                (
                    f"CAPA 점수 {scores.capa_score}/5: ROP "
                    f"{calc.recommended_rop:.1f} ≤ MaxCap {calc.max_rop_cap} "
                    f"(ROP 캡 없음). 1회 발주량만 MaxCap으로 축소 → "
                    f"Q={calc.suggested_order_qty:g}."
                ),
                (
                    f"cycle={calc.order_cycle_days:g}d · {calc.order_days_label}. "
                    f"다회 소량 발주 경로 활성 (Q-only clamp)."
                ),
            ]
            capa_summary = "1회 발주량 상한 → 다회 소량 발주 전환"
    else:
        capa_points = [
            (
                f"추천 ROP {calc.recommended_rop:.1f}개는 CAPA 점수 "
                f"{scores.capa_score}/5 범위에서 수용 가능."
            ),
            (
                f"수요 집중도 {scores.demand_concentration}/5 · "
                f"일평균 소진 {calc.daily_demand:g} 기준 적재 리스크 낮음."
            ),
        ]
        capa_summary = "수용 가능 확인 (안전)"

    capa_block = EvidenceBlock(
        id="capa_filter",
        title="매장 규모(CAPA)에 따른 운영 제약 필터링",
        calc_summary=capa_summary,
        points=capa_points,
    )
    return [lt_block, rop_block, _geo_technical(calc), capa_block]


def _one_liner_plain(summary: StoreSummary, calc: CalcBreakdown) -> str:
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


def _one_liner_technical(summary: StoreSummary, calc: CalcBreakdown) -> str:
    std_ss = _standard_safety_stock(calc)
    ss_delta = calc.store_safety_stock - std_ss
    sign_rop = "▲" if calc.rop_delta >= 0 else "▼"
    sign_ss = "▲" if ss_delta >= 0 else "▼"
    base = (
        f"[{summary.product_name}] LT {calc.standard_lead_time_days:.1f}일(입력 유지) · "
        f"ROP {calc.recommended_rop:.0f}개"
        f"({sign_rop}{abs(calc.rop_delta):.0f}) · "
        f"SS {calc.store_safety_stock:.0f}개"
        f"({sign_ss}{abs(ss_delta):.0f}) · "
        f"발주 {calc.order_days_label} · Q {calc.suggested_order_qty:g} · "
        f"SL {calc.knowledge.service_level_z:.2f}→Z {calc.knowledge.safety_z_factor:.2f}"
    )
    if calc.geo.enabled and not calc.geo.used_fallback and calc.geo.foot_traffic_index > 0:
        base += f" · FTI {calc.geo.foot_traffic_index:.2f}"
    if calc.multi_order_suggestion:
        return f"{base}. CAPA 협소 → MaxCap 고정·다회 소량 발주."
    return f"{base}. 조정 레버: ROP·SS·Q·cycle·SL."


def render(validated: ValidatedInput, calc: CalcBreakdown) -> RecommendationResult:
    summary = _summary(validated, calc)
    guidance = list(validated.guidance)
    if calc.geo.enabled and calc.geo.used_fallback:
        guidance.extend(calc.geo.notes)
    return RecommendationResult(
        recommendation=_one_liner_plain(summary, calc),
        recommendation_technical=_one_liner_technical(summary, calc),
        template_id=validated.template_id,
        template_version=validated.template_version,
        guidance=guidance,
        summary=summary,
        comparison=_comparison_plain(calc),
        comparison_technical=_comparison_technical(calc),
        evidence=_evidence_plain(validated, calc),
        evidence_technical=_evidence_technical(validated, calc),
        calc=calc,
    )
