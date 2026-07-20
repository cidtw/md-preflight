"""Unit tests for demo anchor survey helpers (no live Kakao)."""

from __future__ import annotations

from app.pipeline.demo_anchor_survey import (
    DEFAULT_ANCHOR_ADDRESS,
    SurveyedStore,
    _classify_hyper,
    _classify_sm_ssm,
    _dong_from_address,
    _infer_accessibility,
    _infer_trade_area,
    _is_noise_poi,
    reclassify_store_channel,
    surveyed_store_to_parameters,
)


def test_default_anchor_address() -> None:
    assert "세솔로 25" in DEFAULT_ANCHOR_ADDRESS
    assert "덕양구" in DEFAULT_ANCHOR_ADDRESS


def test_classify_sm_ssm_and_hyper() -> None:
    assert _classify_sm_ssm("이마트에브리데이 행신점", "슈퍼마켓") == "ssm"
    assert _classify_sm_ssm("우리동네슈퍼", "가정,생활 > 슈퍼마켓") == "supermarket"
    assert _classify_sm_ssm("GS25 테스트", "편의점") is None
    assert _classify_hyper("이마트 화정점", "대형마트") is True
    assert _classify_hyper("홈플러스 익스프레스 행신", "슈퍼") is False


def test_classify_lotte_super_fresh_is_ssm_not_hyper() -> None:
    name = "롯데슈퍼프레시 고양삼송점"
    cat = "가정,생활 > 슈퍼마켓 > 대형슈퍼 > 롯데슈퍼프레시"
    assert _classify_hyper(name, cat) is False
    assert _classify_sm_ssm(name, cat) == "ssm"
    assert reclassify_store_channel(name, cat, current="hypermarket") == "ssm"


def test_classify_iga_is_supermarket_not_convenience() -> None:
    name = "IGA마트 고양동세로점"
    cat = "가정,생활 > 편의점 > IGA마트"
    assert _classify_sm_ssm(name, cat) == "supermarket"
    assert reclassify_store_channel(name, cat, current="convenience") == "supermarket"


def test_classify_noise_pois_dropped() -> None:
    fixtures = [
        ("큐사랑 삼송이마트에브리데이점", "가정,생활 > 미용 > 미용실"),
        ("슈퍼해피독 강아지유치원 & 호텔", "가정,생활 > 반려동물 > 반려견놀이터"),
        ("롯데슈퍼 고양삼송점 전기차충전소", "교통,수송 > 자동차 > 전기차 충전소"),
        ("롯데슈퍼 고양삼송점 주차장", "교통,수송 > 교통시설 > 주차장"),
        ("슈퍼드라이 롯데몰은평점", "가정,생활 > 패션 > 의류판매"),
    ]
    for name, cat in fixtures:
        assert _is_noise_poi(name, cat) is True, name
        assert reclassify_store_channel(name, cat) is None, name


def test_infer_accessibility_and_trade() -> None:
    assert _infer_accessibility("XX점", "충장로 100", "") == "main_road"
    assert _infer_accessibility("몰점", "지하상가", "쇼핑몰") == "indoor"
    trade, notes = _infer_trade_area(
        context_cats=["지하철역", "아파트"],
        context_names=["행신역", "서정마을"],
    )
    assert trade in {"office", "residential", "suburban", "campus", "tourist"}
    assert notes


def test_dong_from_address() -> None:
    from app.pipeline.demo_anchor_survey import normalize_location_dong

    dong = _dong_from_address(
        "경기 고양시 덕양구 세솔로 25",
        "경기 고양시 덕양구 행신동 123",
    )
    assert "덕양구" in dong or "행신" in dong
    assert "경기도 경기" not in dong
    assert normalize_location_dong("경기도 경기 고양시 덕양구 동산동") == (
        "경기도 고양시 덕양구 동산동"
    )
    assert normalize_location_dong("경기 고양시 덕양구 동산동").startswith("경기도")


def test_surveyed_store_to_parameters() -> None:
    store = SurveyedStore(
        id="anchor-test",
        place_id="1",
        name="테스트편의점",
        channel="convenience",
        distance_m=120,
        road_address="경기 고양시 덕양구 세솔로 10",
        location_dong="경기도 고양시 덕양구 행신동",
        trade_area="residential",
        accessibility="main_road",
        store_size="cv_s",
        avg_ticket="t_le_8k",
        product_name="냉장 간편식 도시락",
        daily_demand=12,
        standard_lead_time_days=1.5,
    )
    p = surveyed_store_to_parameters(store)
    assert p["use_precise_location"] is True
    assert p["store_address"] == "경기 고양시 덕양구 세솔로 10"
    assert p["store_type"] == "convenience"
