"""Kakao Local place/address search for store picker autocomplete.

Used by the precise-location UI so operators can type a partial store name
(e.g. "GS25 뉴서강") or road/jibun fragment after selecting sido/sigungu/dong
and pick the best official place + road address.
"""

# urllib response types are untyped (Any); keep reportAny off for this adapter only.
# pyright: reportAny=false

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import cast

from pydantic import BaseModel, Field

from app.pipeline.region_catalog import region_prefix

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT_S = 2.5
_MAX_RESULTS = 12
_PROVIDER_UA = "md-preflight-rop/0.3"

JsonObject = dict[str, object]
JsonFetch = Callable[[str, Mapping[str, str]], JsonObject]

# Bias keyword search toward retail formats by store_type.
_STORE_TYPE_QUERY_HINT: dict[str, str] = {
    "convenience": "편의점",
    "supermarket": "슈퍼마켓",
    "ssm": "슈퍼",
    "hypermarket": "마트",
}


class PlaceSuggestion(BaseModel):
    place_id: str
    name: str
    road_address: str = ""
    jibun_address: str = ""
    address_display: str = ""
    category_name: str = ""
    phone: str = ""
    lat: float | None = None
    lng: float | None = None
    score: float = 0.0
    source: str = "keyword"  # keyword | address


class PlaceSearchResponse(BaseModel):
    query: str
    region: str = ""
    results: list[PlaceSuggestion] = Field(default_factory=list)
    used_fallback: bool = False
    notes: list[str] = Field(default_factory=list)


class DongSuggestion(BaseModel):
    name: str
    full_label: str = ""


class DongSearchResponse(BaseModel):
    results: list[DongSuggestion] = Field(default_factory=list)
    used_fallback: bool = False
    notes: list[str] = Field(default_factory=list)


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


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"KakaoAK {api_key}",
        "User-Agent": _PROVIDER_UA,
    }


def _http_get_json(
    url: str,
    headers: Mapping[str, str],
    *,
    timeout: float = _HTTP_TIMEOUT_S,
) -> JsonObject:
    req = urllib.request.Request(url, headers=dict(headers), method="GET")
    response = urllib.request.urlopen(req, timeout=timeout)
    try:
        raw_obj = response.read()
    finally:
        _ = response.close()
    if not isinstance(raw_obj, (bytes, bytearray)):
        msg = "Unexpected HTTP body type"
        raise TypeError(msg)
    payload: object = json.loads(bytes(raw_obj).decode("utf-8"))
    mapped = _as_mapping(payload)
    if mapped is None:
        msg = "Unexpected Kakao API payload type"
        raise TypeError(msg)
    return dict(mapped)


def _similarity(query: str, name: str, address: str) -> float:
    """Lightweight rank: substring boosts + token overlap (no external deps)."""
    q = re.sub(r"\s+", "", query.lower())
    n = re.sub(r"\s+", "", name.lower())
    a = re.sub(r"\s+", "", address.lower())
    if not q:
        return 0.0
    score = 0.0
    if q in n:
        score += 1.2
    if q in a:
        score += 0.6
    if n.startswith(q) or q.startswith(n[: max(2, len(q) // 2)]):
        score += 0.4
    tokens = [t for t in re.split(r"[\s/·]+", query.strip().lower()) if t]
    for t in tokens:
        if t in n:
            score += 0.35
        elif t in a:
            score += 0.15
    score += max(0.0, 0.2 - len(n) / 500.0)
    return round(score, 4)


def _parse_keyword_doc(doc: Mapping[str, object], *, query: str) -> PlaceSuggestion | None:
    name_raw = doc.get("place_name")
    name = str(name_raw).strip() if name_raw is not None else ""
    if not name:
        return None
    road = str(doc.get("road_address_name") or "").strip()
    jibun = str(doc.get("address_name") or "").strip()
    display = road or jibun
    if not display:
        return None
    cat = str(doc.get("category_name") or "").strip()
    phone = str(doc.get("phone") or "").strip()
    place_id = str(doc.get("id") or f"{name}|{display}")
    lat = _as_float(doc.get("y"))
    lng = _as_float(doc.get("x"))
    return PlaceSuggestion(
        place_id=place_id,
        name=name,
        road_address=road,
        jibun_address=jibun,
        address_display=display,
        category_name=cat,
        phone=phone,
        lat=lat,
        lng=lng,
        score=_similarity(query, name, display),
        source="keyword",
    )


def _parse_address_doc(doc: Mapping[str, object], *, query: str) -> PlaceSuggestion | None:
    address_name = str(doc.get("address_name") or "").strip()
    road_obj = _as_mapping(doc.get("road_address"))
    road = ""
    if road_obj is not None:
        road = str(road_obj.get("address_name") or "").strip()
    display = road or address_name
    if not display:
        return None
    lat = _as_float(doc.get("y"))
    lng = _as_float(doc.get("x"))
    label = road or address_name
    return PlaceSuggestion(
        place_id=f"addr|{display}",
        name=label,
        road_address=road,
        jibun_address=address_name,
        address_display=display,
        category_name="주소",
        phone="",
        lat=lat,
        lng=lng,
        score=_similarity(query, label, display) * 0.85,
        source="address",
    )


def search_places(
    query: str,
    *,
    api_key: str | None,
    sido: str = "",
    sigungu: str = "",
    dong: str = "",
    store_type: str = "",
    fetch: JsonFetch | None = None,
    size: int = _MAX_RESULTS,
) -> PlaceSearchResponse:
    cleaned = query.strip()
    region = region_prefix(sido=sido, sigungu=sigungu, dong=dong)
    if len(cleaned) < 1 and not region:
        return PlaceSearchResponse(
            query=cleaned,
            region=region,
            notes=["검색어 또는 지역을 입력해 주세요."],
        )
    if not api_key:
        return PlaceSearchResponse(
            query=cleaned,
            region=region,
            used_fallback=True,
            notes=[
                "KAKAO_REST_API_KEY가 없어 점포 검색을 사용할 수 없습니다. "
                + "주소를 직접 입력해 주세요.",
            ],
        )

    def default_fetch(url: str, headers: Mapping[str, str]) -> JsonObject:
        return _http_get_json(url, headers)

    do_fetch: JsonFetch = fetch or default_fetch
    hint = _STORE_TYPE_QUERY_HINT.get(store_type, "")
    parts = [p for p in (region, cleaned) if p]
    base_q = " ".join(parts).strip() or (region or cleaned)

    results: list[PlaceSuggestion] = []
    notes: list[str] = []

    def _keyword(q: str) -> None:
        params = urllib.parse.urlencode(
            {
                "query": q,
                "size": str(min(15, max(1, size))),
                "page": "1",
            },
        )
        url = f"https://dapi.kakao.com/v2/local/search/keyword.json?{params}"
        data = do_fetch(url, _auth_headers(api_key))
        docs = _as_sequence(data.get("documents")) or []
        for item in docs:
            mapped = _as_mapping(item)
            if mapped is None:
                continue
            sug = _parse_keyword_doc(mapped, query=cleaned or base_q)
            if sug is not None:
                results.append(sug)

    def _address(q: str) -> None:
        params = urllib.parse.urlencode(
            {"query": q, "size": str(min(15, max(1, size)))},
        )
        url = f"https://dapi.kakao.com/v2/local/search/address.json?{params}"
        data = do_fetch(url, _auth_headers(api_key))
        docs = _as_sequence(data.get("documents")) or []
        for item in docs:
            mapped = _as_mapping(item)
            if mapped is None:
                continue
            sug = _parse_address_doc(mapped, query=cleaned or base_q)
            if sug is not None:
                results.append(sug)

    try:
        _keyword(base_q)
        if len(results) < 3 and hint and cleaned:
            _keyword(f"{region} {cleaned} {hint}".strip())
        if len(results) < 5 and (cleaned or region):
            _address(base_q)
    except (urllib.error.URLError, TimeoutError, TypeError, ValueError, RuntimeError) as exc:
        logger.warning("place search failed: %s", exc)
        return PlaceSearchResponse(
            query=cleaned,
            region=region,
            used_fallback=True,
            notes=[f"점포 검색 실패: {exc}"],
        )

    by_key: dict[str, PlaceSuggestion] = {}
    for item in results:
        key = f"{item.name}|{item.address_display}"
        prev = by_key.get(key)
        if prev is None or item.score > prev.score:
            by_key[key] = item
    ranked = sorted(by_key.values(), key=lambda p: (-p.score, p.name))[:size]
    if not ranked:
        notes.append(
            "검색 결과가 없습니다. 지역을 좁히거나 점포명·도로명을 더 입력해 보세요.",
        )
    else:
        notes.append(f"Kakao Local 점포/주소 후보 {len(ranked)}건")
    return PlaceSearchResponse(
        query=cleaned,
        region=region,
        results=ranked,
        notes=notes,
    )


def _collect_dongs_from_docs(
    docs: Sequence[object],
    *,
    sido: str,
    sigungu: str,
    q_strip: str,
    seen: set[str],
    out: list[DongSuggestion],
) -> None:
    for item in docs:
        mapped = _as_mapping(item)
        if mapped is None:
            continue
        candidates: list[str] = []
        for key in ("address", "road_address"):
            block = _as_mapping(mapped.get(key))
            if block is None:
                continue
            dong = str(block.get("region_3depth_name") or "").strip()
            if dong:
                candidates.append(dong)
        # Keyword/place docs expose address_name like "서울 마포구 신수동 12-3".
        for addr_key in ("address_name", "road_address_name"):
            addr = str(mapped.get(addr_key) or "").strip()
            if not addr:
                continue
            parts = addr.split()
            # Find token after sigungu (or 3rd token) that looks like dong/eup/myeon/ri.
            for i, tok in enumerate(parts):
                if re.search(r"(동|읍|면|리|가)$", tok) and (
                    tok in sigungu or i >= 2
                ):
                    candidates.append(tok)
            if len(parts) >= 3 and re.search(r"(동|읍|면|리|가)$", parts[2]):
                candidates.append(parts[2])
        for dong in candidates:
            dong = dong.strip()
            if not dong or dong in seen:
                continue
            if q_strip and q_strip not in dong and not dong.startswith(q_strip):
                continue
            # Drop pure numbers / road names.
            if re.fullmatch(r"\d+.*", dong) or (
                "로" in dong and not dong.endswith(("동", "읍", "면", "리", "가"))
            ):
                continue
            seen.add(dong)
            out.append(
                DongSuggestion(
                    name=dong,
                    full_label=f"{sido} {sigungu} {dong}".strip(),
                ),
            )


def search_dong(
    *,
    api_key: str | None,
    sido: str,
    sigungu: str,
    q: str = "",
    fetch: JsonFetch | None = None,
) -> DongSearchResponse:
    """Suggest eup/myeon/dong/ri under a selected sigungu via Kakao (multi-query)."""
    if not sido.strip() or not sigungu.strip():
        return DongSearchResponse(notes=["시·도와 시·군·구를 먼저 선택해 주세요."])
    if not api_key:
        return DongSearchResponse(
            used_fallback=True,
            notes=["KAKAO_REST_API_KEY가 없어 읍·면·동 자동완성을 사용할 수 없습니다."],
        )

    def default_fetch(url: str, headers: Mapping[str, str]) -> JsonObject:
        return _http_get_json(url, headers)

    do_fetch: JsonFetch = fetch or default_fetch
    q_strip = q.strip()
    sido_s = sido.strip()
    sigungu_s = sigungu.strip()
    seen: set[str] = set()
    out: list[DongSuggestion] = []

    # Multiple query shapes: plain region, with user fragment, keyword "동".
    queries = [
        f"{sido_s} {sigungu_s} {q_strip}".strip(),
        f"{sigungu_s} {q_strip}".strip() if q_strip else f"{sigungu_s}",
        f"{sido_s} {sigungu_s} 동",
    ]
    # Deduplicate while preserving order.
    seen_q: set[str] = set()
    uniq_queries = [x for x in queries if x and not (x in seen_q or seen_q.add(x))]

    try:
        for query in uniq_queries:
            # Address search
            params = urllib.parse.urlencode({"query": query, "size": "15"})
            url = f"https://dapi.kakao.com/v2/local/search/address.json?{params}"
            data = do_fetch(url, _auth_headers(api_key))
            docs = _as_sequence(data.get("documents")) or []
            _collect_dongs_from_docs(
                docs,
                sido=sido_s,
                sigungu=sigungu_s,
                q_strip=q_strip,
                seen=seen,
                out=out,
            )
            # Keyword search (places carry address_name with dong tokens)
            kparams = urllib.parse.urlencode(
                {"query": query, "size": "15", "page": "1"},
            )
            kurl = f"https://dapi.kakao.com/v2/local/search/keyword.json?{kparams}"
            kdata = do_fetch(kurl, _auth_headers(api_key))
            kdocs = _as_sequence(kdata.get("documents")) or []
            _collect_dongs_from_docs(
                kdocs,
                sido=sido_s,
                sigungu=sigungu_s,
                q_strip=q_strip,
                seen=seen,
                out=out,
            )
            if len(out) >= 20:
                break
    except (urllib.error.URLError, TimeoutError, TypeError, ValueError) as exc:
        if out:
            return DongSearchResponse(
                results=out[:25],
                notes=[f"읍·면·동 후보 {len(out)}건 (부분 결과 · {exc})"],
            )
        return DongSearchResponse(used_fallback=True, notes=[f"동 검색 실패: {exc}"])

    if not out:
        return DongSearchResponse(
            results=[],
            notes=[
                "읍·면·동 후보를 찾지 못했습니다. 직접 입력하거나 "
                + "아래 점포 검색으로 주소를 고르면 자동 반영됩니다.",
            ],
        )
    out.sort(key=lambda d: d.name)
    return DongSearchResponse(results=out[:25], notes=[f"읍·면·동 후보 {len(out)}건"])
