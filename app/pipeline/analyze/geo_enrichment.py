"""Kakao Local API geocode + nearby POI enrichment for precise store addresses.

Replaces Google Maps. Uses:
  - GET /v2/local/search/address.json
  - GET /v2/local/search/category.json
  - GET /v2/local/search/keyword.json  (bus stops)

Docs: https://developers.kakao.com/docs/latest/ko/local/dev-guide
"""

# urllib response types are untyped (Any); keep reportAny off for this adapter only.
# pyright: reportAny=false

from __future__ import annotations

import contextlib
import json
import logging
import math
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import cast

from app.pipeline.analyze.competition_saturation import (
    CompetitorQuery,
    classify_competitor,
    competitor_queries,
    profile_for_store_type,
    score_competitors,
)
from app.pipeline.analyze.event_foot_traffic import (
    EVENT_KEYWORD_QUERIES,
    EVENT_SCAN_RADIUS_M,
    classify_event_venue,
    score_event_venues,
)
from app.pipeline.types import (
    CompetitionCompetitor,
    EventVenueSignal,
    GeoEnrichment,
    NearbyPoi,
    PoiCategory,
)

logger = logging.getLogger(__name__)

# Cap wall-clock for nearby POI fan-out (geocode is outside this budget).
_POI_TOTAL_BUDGET_S = 4.0
_HTTP_TIMEOUT_S = 2.5
_POI_MAX_WORKERS = 6

JsonObject = dict[str, object]
# (url, headers) -> JSON object
JsonFetch = Callable[[str, Mapping[str, str]], JsonObject]

# Base weights: transit-first, dense low-signal POIs (편의점·버스) stay modest.
CATEGORY_WEIGHT: dict[PoiCategory, float] = {
    "transit_rail": 1.0,
    "transit_bus": 0.4,
    "retail_anchor": 0.65,
    "convenience": 0.22,
    "office": 0.45,
    "education": 0.35,
    "landmark": 0.35,
    "other": 0.15,
}

# Cap how many nearest POIs of each category enter the score (anti-spam).
_MAX_PER_CATEGORY: dict[PoiCategory, int] = {
    "transit_rail": 2,
    "transit_bus": 2,
    "retail_anchor": 2,
    "convenience": 2,
    "office": 2,
    "education": 2,
    "landmark": 1,
    "other": 1,
}

# 2nd nearest same-category POI gets half the contribution, 3rd gets 1/4, …
_WITHIN_CATEGORY_DECAY = 0.5

# Soft half-saturation: index = raw / (raw + H). raw=H → 0.5; hard 1.0 only as raw→∞.
_HALF_SATURATION = 2.4
_DECAY_METERS = 250.0
_PROVIDER = "kakao"

# Kakao category_group_code → internal category
# https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-category
_KAKAO_CATEGORY_MAP: dict[str, PoiCategory] = {
    "SW8": "transit_rail",  # 지하철역
    "MT1": "retail_anchor",  # 대형마트
    "CS2": "convenience",  # 편의점 (밀도 신호, 저가중)
    "SC4": "education",  # 학교
    "AC5": "education",  # 학원
    "AT4": "landmark",  # 관광명소
    "CT1": "landmark",  # 문화시설
    "PO3": "office",  # 공공기관
    "BK9": "office",  # 은행
}

_CATEGORY_QUERIES: tuple[str, ...] = (
    "SW8",
    "MT1",
    "SC4",
    "AC5",
    "AT4",
    "CT1",
    "PO3",
    "CS2",
)


def _as_mapping(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, object] = {}
    for key, item in cast(dict[object, object], value).items():
        out[str(key)] = item
    return out


def _as_sequence(value: object) -> Sequence[object] | None:
    if not isinstance(value, list):
        return None
    return cast(list[object], value)


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _http_get_json(
    url: str,
    headers: Mapping[str, str],
    *,
    timeout: float = _HTTP_TIMEOUT_S,
) -> JsonObject:
    req = urllib.request.Request(
        url,
        headers=dict(headers),
        method="GET",
    )
    response = urllib.request.urlopen(req, timeout=timeout)
    try:
        raw_obj = response.read()
    finally:
        _ = response.close()
    if not isinstance(raw_obj, (bytes, bytearray)):
        msg = "Unexpected HTTP body type"
        raise TypeError(msg)
    text = bytes(raw_obj).decode("utf-8")
    payload: object = json.loads(text)
    mapped = _as_mapping(payload)
    if mapped is None:
        msg = "Unexpected Kakao API payload type"
        raise TypeError(msg)
    return dict(mapped)


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def map_kakao_category(category_group_code: str) -> PoiCategory:
    return _KAKAO_CATEGORY_MAP.get(category_group_code, "other")


def _select_scoring_pois(pois: list[NearbyPoi]) -> list[NearbyPoi]:
    """Nearest N per category only — keeps dense-urban spam from dominating raw."""
    by_cat: dict[PoiCategory, list[NearbyPoi]] = {}
    for poi in sorted(pois, key=lambda p: p.distance_m):
        bucket = by_cat.setdefault(poi.category, [])
        limit = _MAX_PER_CATEGORY.get(poi.category, 1)
        if len(bucket) < limit:
            bucket.append(poi)
    selected: list[NearbyPoi] = []
    for bucket in by_cat.values():
        selected.extend(bucket)
    return selected


def compute_foot_traffic_index(pois: list[NearbyPoi]) -> float:
    """Conservative foot-traffic score in [0, 1].

    Steps:
      1. Keep nearest N POIs per category (anti-saturation).
      2. raw = Σ w(cat) * exp(-d/250) * 0.5^rank_within_category
      3. index = raw / (raw + half_saturation)  — soft ceiling, rare hard 1.0
    """
    if not pois:
        return 0.0

    selected = _select_scoring_pois(pois)
    by_cat: dict[PoiCategory, list[NearbyPoi]] = {}
    for poi in selected:
        by_cat.setdefault(poi.category, []).append(poi)

    raw = 0.0
    for category, group in by_cat.items():
        weight = CATEGORY_WEIGHT.get(category, CATEGORY_WEIGHT["other"])
        ordered = sorted(group, key=lambda p: p.distance_m)
        for rank, poi in enumerate(ordered):
            distance_factor = math.exp(-max(0.0, poi.distance_m) / _DECAY_METERS)
            rank_factor = _WITHIN_CATEGORY_DECAY**rank
            raw += weight * distance_factor * rank_factor

    if raw <= 0.0:
        return 0.0
    # Soft saturation: mid-density lands mid-scale; extreme clusters approach 1.
    index = raw / (raw + _HALF_SATURATION)
    return round(min(1.0, max(0.0, index)), 4)


def disabled_enrichment(*, notes: list[str] | None = None) -> GeoEnrichment:
    return GeoEnrichment(
        enabled=False,
        used_fallback=True,
        provider="none",
        notes=list(notes or ["정확한 위치 미사용 — 행정동·상권 점수만 적용"]),
    )


def fallback_enrichment(
    *,
    address: str | None,
    notes: list[str],
    provider: str = _PROVIDER,
) -> GeoEnrichment:
    return GeoEnrichment(
        enabled=True,
        used_fallback=True,
        provider=provider,
        address_queried=address,
        notes=notes,
        foot_traffic_index=0.0,
        pois=[],
    )


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"KakaoAK {api_key}",
        "User-Agent": "md-preflight-rop/0.3",
    }


def _geocode_address(
    address: str,
    *,
    api_key: str,
    fetch: JsonFetch,
) -> tuple[float, float, str]:
    query = urllib.parse.urlencode({"query": address})
    url = f"https://dapi.kakao.com/v2/local/search/address.json?{query}"
    data = fetch(url, _auth_headers(api_key))
    documents = _as_sequence(data.get("documents"))
    if documents is None or not documents:
        msg = "Kakao address search returned no results"
        raise RuntimeError(msg)
    first = _as_mapping(documents[0])
    if first is None:
        msg = "Invalid Kakao address document"
        raise RuntimeError(msg)
    lng = _as_float(first.get("x"))
    lat = _as_float(first.get("y"))
    if lat is None or lng is None:
        msg = "Kakao address missing coordinates"
        raise RuntimeError(msg)
    label = address
    address_name = first.get("address_name")
    if isinstance(address_name, str) and address_name.strip():
        label = address_name.strip()
    else:
        road = first.get("road_address")
        road_map = _as_mapping(road)
        if road_map is not None:
            road_name = road_map.get("address_name")
            if isinstance(road_name, str) and road_name.strip():
                label = road_name.strip()
    return lat, lng, label


def _parse_place_docs(
    documents: Sequence[object],
    *,
    default_category: PoiCategory,
    force_category: PoiCategory | None = None,
) -> list[NearbyPoi]:
    pois: list[NearbyPoi] = []
    for item in documents:
        doc = _as_mapping(item)
        if doc is None:
            continue
        name_raw = doc.get("place_name")
        name = str(name_raw).strip() if name_raw is not None else ""
        if not name:
            continue
        distance = _as_float(doc.get("distance"))
        if distance is None:
            continue
        if force_category is not None:
            category = force_category
        else:
            code = str(doc.get("category_group_code") or "")
            category = map_kakao_category(code) if code else default_category
        pois.append(
            NearbyPoi(
                category=category,
                name=name,
                distance_m=round(distance, 1),
            ),
        )
    return pois


def _search_category(
    *,
    lat: float,
    lng: float,
    category_code: str,
    radius_m: int,
    api_key: str,
    fetch: JsonFetch,
) -> list[NearbyPoi]:
    query = urllib.parse.urlencode(
        {
            "category_group_code": category_code,
            "x": f"{lng}",
            "y": f"{lat}",
            "radius": str(radius_m),
            "size": "15",
            "sort": "distance",
        },
    )
    url = f"https://dapi.kakao.com/v2/local/search/category.json?{query}"
    data = fetch(url, _auth_headers(api_key))
    documents = _as_sequence(data.get("documents"))
    if documents is None:
        return []
    default = map_kakao_category(category_code)
    return _parse_place_docs(documents, default_category=default)


def _search_keyword_bus(
    *,
    lat: float,
    lng: float,
    radius_m: int,
    api_key: str,
    fetch: JsonFetch,
) -> list[NearbyPoi]:
    """Bus stops are not a standard category_group_code — keyword search."""
    query = urllib.parse.urlencode(
        {
            "query": "버스정류장",
            "x": f"{lng}",
            "y": f"{lat}",
            "radius": str(radius_m),
            "size": "15",
            "sort": "distance",
        },
    )
    url = f"https://dapi.kakao.com/v2/local/search/keyword.json?{query}"
    data = fetch(url, _auth_headers(api_key))
    documents = _as_sequence(data.get("documents"))
    if documents is None:
        return []
    return _parse_place_docs(
        documents,
        default_category="transit_bus",
        force_category="transit_bus",
    )


def _search_keyword_places(
    *,
    lat: float,
    lng: float,
    radius_m: int,
    keyword: str,
    api_key: str,
    fetch: JsonFetch,
) -> list[tuple[str, float, str]]:
    """Return (name, distance_m, query) hits for event-venue keyword scan."""
    query = urllib.parse.urlencode(
        {
            "query": keyword,
            "x": f"{lng}",
            "y": f"{lat}",
            "radius": str(radius_m),
            "size": "10",
            "sort": "distance",
        },
    )
    url = f"https://dapi.kakao.com/v2/local/search/keyword.json?{query}"
    data = fetch(url, _auth_headers(api_key))
    documents = _as_sequence(data.get("documents"))
    if documents is None:
        return []
    out: list[tuple[str, float, str]] = []
    for item in documents:
        doc = _as_mapping(item)
        if doc is None:
            continue
        name_raw = doc.get("place_name")
        name = str(name_raw).strip() if name_raw is not None else ""
        distance = _as_float(doc.get("distance"))
        if not name or distance is None:
            continue
        out.append((name, float(distance), keyword))
    return out


def _scan_event_venues(
    *,
    lat: float,
    lng: float,
    api_key: str,
    fetch: JsonFetch,
    radius_m: int = EVENT_SCAN_RADIUS_M,
) -> tuple[list[EventVenueSignal], float, float, list[str]]:
    """Search event-crowd venues within radius; return venues, uplift, multiplier, notes."""
    notes: list[str] = []
    raw_hits: list[EventVenueSignal] = []
    pool = ThreadPoolExecutor(max_workers=min(4, len(EVENT_KEYWORD_QUERIES)))
    futures = [
        pool.submit(
            _search_keyword_places,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            keyword=kw,
            api_key=api_key,
            fetch=fetch,
        )
        for kw in EVENT_KEYWORD_QUERIES
    ]
    try:
        try:
            for fut in as_completed(futures, timeout=_POI_TOTAL_BUDGET_S):
                try:
                    for name, distance, kw in fut.result():
                        kind = classify_event_venue(name, query_hint=kw)
                        if kind is None:
                            continue
                        if distance > radius_m * 1.05:
                            continue
                        raw_hits.append(
                            EventVenueSignal(
                                name=name,
                                kind=kind,
                                distance_m=round(distance, 1),
                            ),
                        )
                except (
                    urllib.error.URLError,
                    TimeoutError,
                    TypeError,
                    ValueError,
                    RuntimeError,
                ) as sub_exc:
                    logger.warning("kakao event keyword failed: %s", sub_exc)
        except FuturesTimeoutError:
            notes.append(
                f"행사·유동 시설 검색 예산({_POI_TOTAL_BUDGET_S:.0f}s) 초과 — 부분 결과 사용",
            )
            for fut in futures:
                if fut.done() and not fut.cancelled():
                    with contextlib.suppress(Exception):
                        for name, distance, kw in fut.result(timeout=0):
                            kind = classify_event_venue(name, query_hint=kw)
                            if kind is None or distance > radius_m * 1.05:
                                continue
                            raw_hits.append(
                                EventVenueSignal(
                                    name=name,
                                    kind=kind,
                                    distance_m=round(distance, 1),
                                ),
                            )
                else:
                    _ = fut.cancel()
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    # Dedupe by name, keep nearest.
    by_name: dict[str, EventVenueSignal] = {}
    for hit in sorted(raw_hits, key=lambda v: v.distance_m):
        if hit.name not in by_name:
            by_name[hit.name] = hit

    uplift, multiplier, scored = score_event_venues(
        list(by_name.values()),
        radius_m=radius_m,
    )
    if scored:
        top_names = ", ".join(f"{v.name}({v.kind}/{v.distance_m:.0f}m)" for v in scored[:3])
        notes.append(
            (
                f"반경 {radius_m}m 내 임시 유동 가능 시설 {len(scored)}곳 · "
                + f"증분지수 {uplift:.3f} · 수요배수 {multiplier:.3f} · 상위: {top_names}"
            ),
        )
    else:
        notes.append(
            (
                f"반경 {radius_m}m 내 대형 행사·유동 유발 시설이 검색되지 않아 "
                + "일시 유동 증분을 0으로 둡니다."
            ),
        )
    return scored, uplift, multiplier, notes


def _scan_competitors(
    *,
    lat: float,
    lng: float,
    store_type: str,
    api_key: str,
    fetch: JsonFetch,
) -> tuple[list[CompetitionCompetitor], float, float, int, int, list[str]]:
    """Search competitors by industry matrix; return scored list + intensity + factor."""
    profile = profile_for_store_type(store_type)
    queries = competitor_queries(store_type)
    notes: list[str] = []
    raw_hits: list[CompetitionCompetitor] = []
    workers = min(6, max(1, len(queries)))
    pool = ThreadPoolExecutor(max_workers=workers)

    def _run_one(q: CompetitorQuery) -> list[CompetitionCompetitor]:
        hits: list[CompetitionCompetitor] = []
        if q.mode == "category":
            pois = _search_category(
                lat=lat,
                lng=lng,
                category_code=q.code_or_query,
                radius_m=q.radius_m,
                api_key=api_key,
                fetch=fetch,
            )
            for poi in pois:
                kind = classify_competitor(
                    poi.name,
                    default_kind=q.default_kind,
                    query_hint=q.code_or_query,
                )
                hits.append(
                    CompetitionCompetitor(
                        name=poi.name,
                        kind=kind,
                        tier=q.tier,
                        distance_m=poi.distance_m,
                    ),
                )
            return hits
        places = _search_keyword_places(
            lat=lat,
            lng=lng,
            radius_m=q.radius_m,
            keyword=q.code_or_query,
            api_key=api_key,
            fetch=fetch,
        )
        for name, distance, kw in places:
            kind = classify_competitor(
                name,
                default_kind=q.default_kind,
                query_hint=kw,
            )
            hits.append(
                CompetitionCompetitor(
                    name=name,
                    kind=kind,
                    tier=q.tier,
                    distance_m=round(distance, 1),
                ),
            )
        return hits

    futures = [pool.submit(_run_one, q) for q in queries]
    try:
        try:
            for fut in as_completed(futures, timeout=_POI_TOTAL_BUDGET_S):
                try:
                    raw_hits.extend(fut.result())
                except (
                    urllib.error.URLError,
                    TimeoutError,
                    TypeError,
                    ValueError,
                    RuntimeError,
                ) as sub_exc:
                    logger.warning("kakao competition query failed: %s", sub_exc)
        except FuturesTimeoutError:
            notes.append(
                f"경쟁 매장 검색 예산({_POI_TOTAL_BUDGET_S:.0f}s) 초과 — 부분 결과 사용",
            )
            for fut in futures:
                if fut.done() and not fut.cancelled():
                    with contextlib.suppress(Exception):
                        raw_hits.extend(fut.result(timeout=0))
                else:
                    _ = fut.cancel()
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    intensity, demand_factor, scored = score_competitors(
        raw_hits,
        decay_m=profile.decay_m,
        max_radius_m=profile.search_radius_m,
    )
    if scored:
        top = ", ".join(
            f"{c.name}({c.tier}/{c.distance_m:.0f}m)" for c in scored[:3]
        )
        notes.append(
            (
                f"경쟁 포화 스캔 · 1차 상권 {profile.primary_radius_m}m · "
                f"검색 {profile.search_radius_m}m · 경쟁 {len(scored)}곳 · "
                f"강도 {intensity:.3f} · 수요계수 {demand_factor:.3f} · 상위: {top}"
            ),
        )
        notes.append(profile.notes)
    else:
        notes.append(
            (
                f"경쟁 포화 옵션 활성 · 검색 반경 {profile.search_radius_m}m 안 "
                "동종·위협 경쟁 점포가 검색되지 않아 수요 분산 0으로 둡니다."
            ),
        )
        notes.append(profile.notes)
    return (
        scored,
        intensity,
        demand_factor,
        profile.primary_radius_m,
        profile.search_radius_m,
        notes,
    )


def enrich_from_address(
    address: str,
    *,
    api_key: str | None,
    radius_m: int = 500,
    fetch: JsonFetch | None = None,
    scan_events: bool = False,
    scan_competition: bool = False,
    store_type: str = "convenience",
) -> GeoEnrichment:
    """Geocode address and collect nearby foot-traffic POIs via Kakao Local."""
    cleaned = address.strip()
    if not cleaned:
        return fallback_enrichment(
            address=None,
            notes=["정확한 매장 주소가 비어 있어 행정동 경로로 대체했습니다."],
        )
    if not api_key:
        return fallback_enrichment(
            address=cleaned,
            notes=[
                "KAKAO_REST_API_KEY(또는 MDPREFLIGHT_KAKAO_REST_API_KEY)가 "
                + "설정되지 않아 지도 보강을 건너뛰고 행정동 경로로 계산했습니다.",
            ],
        )

    def default_fetch(url: str, headers: Mapping[str, str]) -> JsonObject:
        return _http_get_json(url, headers)

    do_fetch = fetch or default_fetch

    try:
        lat, lng, resolved = _geocode_address(
            cleaned,
            api_key=api_key,
            fetch=do_fetch,
        )
    except (RuntimeError, TypeError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        logger.exception("kakao geocode failed for %s", cleaned)
        return fallback_enrichment(
            address=cleaned,
            notes=[f"주소 검색 실패로 행정동 경로 사용: {exc}"],
        )

    merged: list[NearbyPoi] = []
    try:
        def _jobs() -> list[Callable[[], list[NearbyPoi]]]:
            jobs: list[Callable[[], list[NearbyPoi]]] = [
                lambda code=code: _search_category(
                    lat=lat,
                    lng=lng,
                    category_code=code,
                    radius_m=radius_m,
                    api_key=api_key,
                    fetch=do_fetch,
                )
                for code in _CATEGORY_QUERIES
            ]
            jobs.append(
                lambda: _search_keyword_bus(
                    lat=lat,
                    lng=lng,
                    radius_m=radius_m,
                    api_key=api_key,
                    fetch=do_fetch,
                ),
            )
            return jobs

        # Do not use `with ThreadPoolExecutor` — its default shutdown(wait=True)
        # would block past the collect budget while straggler HTTP calls finish.
        pool = ThreadPoolExecutor(max_workers=_POI_MAX_WORKERS)
        futures = [pool.submit(job) for job in _jobs()]
        try:
            try:
                for fut in as_completed(futures, timeout=_POI_TOTAL_BUDGET_S):
                    try:
                        merged.extend(fut.result())
                    except (
                        urllib.error.URLError,
                        TimeoutError,
                        TypeError,
                        ValueError,
                        RuntimeError,
                    ) as sub_exc:
                        logger.warning("kakao poi sub-query failed: %s", sub_exc)
            except FuturesTimeoutError:
                logger.warning(
                    "kakao nearby budget %.1fs exceeded for %s; using partial POIs",
                    _POI_TOTAL_BUDGET_S,
                    cleaned,
                )
                for fut in futures:
                    if fut.done() and not fut.cancelled():
                        with contextlib.suppress(Exception):
                            merged.extend(fut.result(timeout=0))
                    else:
                        _ = fut.cancel()
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    except (urllib.error.URLError, TimeoutError, TypeError, ValueError) as exc:
        logger.exception("kakao nearby failed for %s", cleaned)
        return GeoEnrichment(
            enabled=True,
            lat=lat,
            lng=lng,
            address_queried=cleaned,
            provider=_PROVIDER,
            used_fallback=True,
            radius_m=radius_m,
            notes=[f"주변 시설 조회 실패 — 좌표만 확보, 유동 지수 0: {exc}"],
            foot_traffic_index=0.0,
            pois=[],
        )

    # Dedupe by name, keep nearest.
    by_name: dict[str, NearbyPoi] = {}
    for poi in sorted(merged, key=lambda p: p.distance_m):
        if poi.distance_m > radius_m * 1.05:
            continue
        if poi.name not in by_name:
            by_name[poi.name] = poi
    top = sorted(by_name.values(), key=lambda p: p.distance_m)[:20]
    index = compute_foot_traffic_index(top)
    note = (
        f"Kakao Local 반경 {radius_m}m · 주소 '{resolved}' · "
        + f"POI {len(top)}곳 · foot_traffic_index={index:.3f}"
    )
    notes = [note]
    event_venues: list[EventVenueSignal] = []
    event_uplift = 0.0
    event_mult = 1.0
    if scan_events:
        try:
            event_venues, event_uplift, event_mult, event_notes = _scan_event_venues(
                lat=lat,
                lng=lng,
                api_key=api_key,
                fetch=do_fetch,
                radius_m=EVENT_SCAN_RADIUS_M,
            )
            notes.extend(event_notes)
        except (urllib.error.URLError, TimeoutError, TypeError, ValueError) as event_exc:
            logger.warning("event venue scan failed: %s", event_exc)
            notes.append(f"일시 유동 시설 검색 실패 — 증분 0 처리: {event_exc}")

    competitors: list[CompetitionCompetitor] = []
    comp_intensity = 0.0
    comp_factor = 1.0
    comp_primary = 0
    comp_search = 0
    if scan_competition:
        try:
            (
                competitors,
                comp_intensity,
                comp_factor,
                comp_primary,
                comp_search,
                comp_notes,
            ) = _scan_competitors(
                lat=lat,
                lng=lng,
                store_type=store_type,
                api_key=api_key,
                fetch=do_fetch,
            )
            notes.extend(comp_notes)
        except (urllib.error.URLError, TimeoutError, TypeError, ValueError) as comp_exc:
            logger.warning("competition scan failed: %s", comp_exc)
            notes.append(f"경쟁 매장 검색 실패 — 수요 분산 0 처리: {comp_exc}")
            profile = profile_for_store_type(store_type)
            comp_primary = profile.primary_radius_m
            comp_search = profile.search_radius_m

    return GeoEnrichment(
        enabled=True,
        lat=lat,
        lng=lng,
        pois=top,
        foot_traffic_index=index,
        provider=_PROVIDER,
        used_fallback=False,
        notes=notes,
        address_queried=cleaned,
        radius_m=radius_m,
        event_scan_enabled=scan_events,
        event_radius_m=EVENT_SCAN_RADIUS_M,
        event_venues=event_venues,
        event_foot_traffic_uplift=event_uplift,
        event_demand_multiplier=event_mult,
        competition_scan_enabled=scan_competition,
        competition_radius_m=comp_search,
        competition_primary_radius_m=comp_primary,
        competition_store_type=store_type if scan_competition else None,
        competitors=competitors,
        competition_intensity=comp_intensity,
        competition_demand_factor=comp_factor,
    )
