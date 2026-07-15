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

from app.pipeline.types import GeoEnrichment, NearbyPoi, PoiCategory

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


def enrich_from_address(
    address: str,
    *,
    api_key: str | None,
    radius_m: int = 500,
    fetch: JsonFetch | None = None,
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

        with ThreadPoolExecutor(max_workers=_POI_MAX_WORKERS) as pool:
            futures = [pool.submit(job) for job in _jobs()]
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
    return GeoEnrichment(
        enabled=True,
        lat=lat,
        lng=lng,
        pois=top,
        foot_traffic_index=index,
        provider=_PROVIDER,
        used_fallback=False,
        notes=[note],
        address_queried=cleaned,
        radius_m=radius_m,
    )
