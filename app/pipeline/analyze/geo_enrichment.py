"""Google Maps geocode + nearby POI enrichment for precise store addresses."""

# urllib response types are untyped (Any); keep reportAny off for this adapter only.
# pyright: reportAny=false

from __future__ import annotations

import json
import logging
import math
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import cast

from app.pipeline.types import GeoEnrichment, NearbyPoi, PoiCategory

logger = logging.getLogger(__name__)

JsonObject = dict[str, object]
JsonFetch = Callable[[str], JsonObject]

CATEGORY_WEIGHT: dict[PoiCategory, float] = {
    "transit_rail": 1.0,
    "transit_bus": 0.55,
    "retail_anchor": 0.7,
    "office": 0.65,
    "education": 0.5,
    "landmark": 0.45,
    "other": 0.2,
}

_GOOGLE_TYPE_MAP: tuple[tuple[str, PoiCategory], ...] = (
    ("subway_station", "transit_rail"),
    ("train_station", "transit_rail"),
    ("light_rail_station", "transit_rail"),
    ("transit_station", "transit_rail"),
    ("bus_station", "transit_bus"),
    ("bus_stop", "transit_bus"),
    ("shopping_mall", "retail_anchor"),
    ("department_store", "retail_anchor"),
    ("supermarket", "retail_anchor"),
    ("university", "education"),
    ("school", "education"),
    ("secondary_school", "education"),
    ("primary_school", "education"),
    ("tourist_attraction", "landmark"),
    ("museum", "landmark"),
    ("stadium", "landmark"),
    ("park", "landmark"),
    ("accounting", "office"),
    ("lawyer", "office"),
    ("local_government_office", "office"),
    ("finance", "office"),
    ("real_estate_agency", "office"),
)

_NEARBY_TYPES: tuple[str, ...] = (
    "subway_station",
    "train_station",
    "bus_station",
    "transit_station",
    "tourist_attraction",
    "school",
    "university",
    "shopping_mall",
    "department_store",
)

_INDEX_SOFT_CAP = 4.0
_DECAY_METERS = 250.0


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
    return None


def _http_get_json(url: str, *, timeout: float = 8.0) -> JsonObject:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "md-preflight-rop/0.3"},
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
        msg = "Unexpected Google API payload type"
        raise TypeError(msg)
    return dict(mapped)


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def map_google_types(types: list[str]) -> PoiCategory:
    type_set = set(types)
    for google_type, category in _GOOGLE_TYPE_MAP:
        if google_type in type_set:
            return category
    return "other"


def compute_foot_traffic_index(pois: list[NearbyPoi]) -> float:
    """Sum weight(category) * exp(-distance/250), normalized to [0, 1]."""
    if not pois:
        return 0.0
    raw = 0.0
    for poi in pois:
        weight = CATEGORY_WEIGHT.get(poi.category, CATEGORY_WEIGHT["other"])
        raw += weight * math.exp(-max(0.0, poi.distance_m) / _DECAY_METERS)
    return round(min(1.0, max(0.0, raw / _INDEX_SOFT_CAP)), 4)


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
    provider: str = "google",
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


def _geocode(
    address: str,
    *,
    api_key: str,
    fetch: JsonFetch,
) -> tuple[float, float, str]:
    query = urllib.parse.urlencode(
        {"address": address, "key": api_key, "language": "ko"},
    )
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{query}"
    data = fetch(url)
    status = str(data.get("status", ""))
    if status != "OK":
        err = data.get("error_message", "")
        msg = f"Geocoding failed: {status} {err}".strip()
        raise RuntimeError(msg)
    results = _as_sequence(data.get("results"))
    if results is None or not results:
        msg = "Geocoding returned no results"
        raise RuntimeError(msg)
    first = _as_mapping(results[0])
    if first is None:
        msg = "Invalid geocode result"
        raise RuntimeError(msg)
    geometry = _as_mapping(first.get("geometry"))
    if geometry is None:
        msg = "Missing geometry"
        raise RuntimeError(msg)
    location = _as_mapping(geometry.get("location"))
    if location is None:
        msg = "Missing location"
        raise RuntimeError(msg)
    lat = _as_float(location.get("lat"))
    lng = _as_float(location.get("lng"))
    if lat is None or lng is None:
        msg = "Invalid lat/lng"
        raise RuntimeError(msg)
    formatted = first.get("formatted_address")
    label = str(formatted) if formatted is not None else address
    return lat, lng, label


def _nearby_for_type(
    *,
    lat: float,
    lng: float,
    place_type: str,
    radius_m: int,
    api_key: str,
    fetch: JsonFetch,
) -> list[JsonObject]:
    query = urllib.parse.urlencode(
        {
            "location": f"{lat},{lng}",
            "radius": str(radius_m),
            "type": place_type,
            "key": api_key,
            "language": "ko",
        },
    )
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?{query}"
    data = fetch(url)
    status = str(data.get("status", ""))
    if status in {"ZERO_RESULTS", "OK"}:
        results = _as_sequence(data.get("results"))
        if results is None:
            return []
        out: list[JsonObject] = []
        for item in results:
            mapped = _as_mapping(item)
            if mapped is not None:
                out.append(dict(mapped))
        return out
    logger.warning("Places nearby type=%s status=%s", place_type, status)
    return []


def _pois_from_results(
    results: list[JsonObject],
    *,
    origin_lat: float,
    origin_lng: float,
    radius_m: int,
) -> list[NearbyPoi]:
    seen: set[str] = set()
    pois: list[NearbyPoi] = []
    for item in results:
        name_raw = item.get("name")
        name = str(name_raw).strip() if name_raw is not None else ""
        if not name or name in seen:
            continue
        geometry = _as_mapping(item.get("geometry"))
        if geometry is None:
            continue
        location = _as_mapping(geometry.get("location"))
        if location is None:
            continue
        plat = _as_float(location.get("lat"))
        plng = _as_float(location.get("lng"))
        if plat is None or plng is None:
            continue
        distance = haversine_m(origin_lat, origin_lng, plat, plng)
        if distance > radius_m * 1.05:
            continue
        raw_types = _as_sequence(item.get("types"))
        types = [str(t) for t in raw_types] if raw_types is not None else []
        category = map_google_types(types)
        seen.add(name)
        pois.append(
            NearbyPoi(
                category=category,
                name=name,
                distance_m=round(distance, 1),
            ),
        )
    pois.sort(key=lambda p: p.distance_m)
    return pois


def enrich_from_address(
    address: str,
    *,
    api_key: str | None,
    radius_m: int = 500,
    fetch: JsonFetch | None = None,
) -> GeoEnrichment:
    """Geocode address and collect nearby foot-traffic POIs via Google Maps."""
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
                "GOOGLE_MAPS_API_KEY(또는 MDPREFLIGHT_GOOGLE_MAPS_API_KEY)가 "
                + "설정되지 않아 지도 보강을 건너뛰고 행정동 경로로 계산했습니다.",
            ],
            provider="google",
        )

    do_fetch = fetch or _http_get_json
    try:
        lat, lng, resolved = _geocode(cleaned, api_key=api_key, fetch=do_fetch)
    except (RuntimeError, TypeError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        logger.exception("geocode failed for %s", cleaned)
        return fallback_enrichment(
            address=cleaned,
            notes=[f"주소 지오코딩 실패로 행정동 경로 사용: {exc}"],
            provider="google",
        )

    merged: list[JsonObject] = []
    try:
        for place_type in _NEARBY_TYPES:
            merged.extend(
                _nearby_for_type(
                    lat=lat,
                    lng=lng,
                    place_type=place_type,
                    radius_m=radius_m,
                    api_key=api_key,
                    fetch=do_fetch,
                ),
            )
    except (urllib.error.URLError, TimeoutError, TypeError, ValueError) as exc:
        logger.exception("nearby search failed for %s", cleaned)
        return GeoEnrichment(
            enabled=True,
            lat=lat,
            lng=lng,
            address_queried=cleaned,
            provider="google",
            used_fallback=True,
            radius_m=radius_m,
            notes=[f"주변 시설 조회 실패 — 좌표만 확보, 유동 지수 0: {exc}"],
            foot_traffic_index=0.0,
            pois=[],
        )

    pois = _pois_from_results(
        merged,
        origin_lat=lat,
        origin_lng=lng,
        radius_m=radius_m,
    )
    top = pois[:20]
    index = compute_foot_traffic_index(top)
    note = (
        f"Google Maps 반경 {radius_m}m · 지오코딩 '{resolved}' · "
        + f"POI {len(top)}곳 · foot_traffic_index={index:.3f}"
    )
    return GeoEnrichment(
        enabled=True,
        lat=lat,
        lng=lng,
        pois=top,
        foot_traffic_index=index,
        provider="google",
        used_fallback=False,
        notes=[note],
        address_queried=cleaned,
        radius_m=radius_m,
    )
