"""Census retail near a fixed demo anchor address via Kakao Local.

Anchor (presentation default): 경기도 고양시 덕양구 세솔로 25

Radii (operator request):
  - convenience (CS2): 1 km
  - supermarket / SSM: 3 km (keyword census)
  - hypermarket (MT1 + major chains): 10 km

Each hit is classified and given inferred trade_area / accessibility /
foot-traffic context for ROP demo scenarios. Not live POS sales data.
"""

# pyright: reportAny=false

from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Final, Literal, cast

from pydantic import BaseModel, Field

from app.pipeline.types import ParameterValue

# Top-level import so Vercel Python bundler always packs the census blob.
try:
    from app.data.demo_anchor_survey_blob import SNAPSHOT_JSON as _EMBEDDED_SNAPSHOT_JSON
except ImportError:  # pragma: no cover
    _EMBEDDED_SNAPSHOT_JSON = None

logger = logging.getLogger(__name__)

DEFAULT_ANCHOR_ADDRESS: Final[str] = "경기도 고양시 덕양구 세솔로 25"

RADIUS_CONVENIENCE_M: Final[int] = 1000
RADIUS_SM_SSM_M: Final[int] = 3000
RADIUS_HYPER_M: Final[int] = 10000
# Context POI radius for trade-area / FTI inference around each store
CONTEXT_RADIUS_M: Final[int] = 500

_HTTP_TIMEOUT_S = 4.0
_MAX_PAGES = 45
_PROVIDER_UA = "md-preflight-rop/demo-survey/0.4"

JsonObject = dict[str, object]
JsonFetch = Callable[[str, Mapping[str, str]], JsonObject]

StoreChannel = Literal["convenience", "supermarket", "ssm", "hypermarket"]

_SSM_NAME_MARKERS: Final[tuple[str, ...]] = (
    "이마트에브리데이",
    "이마트 에브리데이",
    "롯데슈퍼",
    "롯데 슈퍼",
    "홈플러스 익스프레스",
    "홈플러스익스프레스",
    "GS더프레시",
    "GS 더프레시",
    "GS THE FRESH",
    "지에스더프레시",
    "농협하나로",
    "하나로마트",
    "홈플러스 미니",
    "코스트코",  # usually hyper; filtered elsewhere
)

_HYPER_NAME_MARKERS: Final[tuple[str, ...]] = (
    "이마트",
    "홈플러스",
    "롯데마트",
    "코스트코",
    "트레이더스",
    "농협하나로클럽",
    "메가마트",
    "탑마트",
)

_SM_KEYWORD_QUERIES: Final[tuple[str, ...]] = (
    "슈퍼마켓",
    "슈퍼",
    "이마트에브리데이",
    "롯데슈퍼",
    "홈플러스 익스프레스",
    "GS더프레시",
    "농협하나로마트",
    "식자재마트",
)

def _snapshot_candidates() -> list[Path]:
    """Resolve snapshot path across local repo and Vercel serverless layouts."""
    here = Path(__file__).resolve()
    candidates = [
        # Preferred: packaged with app/ (always included by Python build)
        here.parents[1] / "data" / "demo_anchor_survey.json",
        here.parents[2] / "data" / "demo_anchor_survey.json",
        Path.cwd() / "data" / "demo_anchor_survey.json",
        Path.cwd() / "app" / "data" / "demo_anchor_survey.json",
        Path("/var/task/app/data/demo_anchor_survey.json"),
        Path("/var/task/data/demo_anchor_survey.json"),
    ]
    try:
        import app as app_pkg

        app_root = Path(app_pkg.__file__).resolve().parent
        candidates.insert(0, app_root / "data" / "demo_anchor_survey.json")
    except Exception:
        pass
    # Debug-friendly: log which exist (once per cold start at most via logger.debug)
    for path in candidates:
        if path.is_file():
            logger.info("demo census snapshot found at %s", path)
            break
    else:
        logger.warning(
            "demo census snapshot missing; tried: %s",
            [str(p) for p in candidates],
        )
    return candidates


_SNAPSHOT_PATH: Final[Path] = _snapshot_candidates()[0]


class SurveyedStore(BaseModel):
    """One retail place near the demo anchor."""

    id: str
    place_id: str
    name: str
    channel: StoreChannel
    distance_m: float
    road_address: str = ""
    jibun_address: str = ""
    address_display: str = ""
    category_name: str = ""
    lat: float | None = None
    lng: float | None = None
    phone: str = ""
    # Inferred ROP inputs
    trade_area: str = "residential"
    accessibility: str = "main_road"
    store_size: str = "cv_s"
    avg_ticket: str = "t_le_8k"
    location_dong: str = ""
    product_name: str = ""
    daily_demand: float = 10.0
    standard_lead_time_days: float = 2.0
    service_level: str = "sl_95"
    # Context signals
    foot_traffic_index: float = 0.0
    context_notes: list[str] = Field(default_factory=list)
    inference_summary: str = ""


class AnchorSurveyResult(BaseModel):
    anchor_address: str
    anchor_lat: float | None = None
    anchor_lng: float | None = None
    anchor_label: str = ""
    surveyed_at: str = ""
    provider: str = "kakao"
    used_live_api: bool = False
    notes: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    stores: list[SurveyedStore] = Field(default_factory=list)


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
    payload: object = json.loads(bytes(raw_obj).decode("utf-8"))
    mapped = _as_mapping(payload)
    if mapped is None:
        msg = "Unexpected Kakao payload"
        raise TypeError(msg)
    return dict(mapped)


def _stable_id(place_id: str, name: str, address: str) -> str:
    raw = f"{place_id}|{name}|{address}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"anchor-{digest}"


def _geocode(
    address: str,
    *,
    api_key: str,
    fetch: JsonFetch,
) -> tuple[float, float, str]:
    query = urllib.parse.urlencode({"query": address})
    url = f"https://dapi.kakao.com/v2/local/search/address.json?{query}"
    data = fetch(url, _auth_headers(api_key))
    documents = _as_sequence(data.get("documents"))
    if documents:
        first = _as_mapping(documents[0])
        if first is not None:
            lat = _as_float(first.get("y"))
            lng = _as_float(first.get("x"))
            if lat is not None and lng is not None:
                label = address
                an = first.get("address_name")
                if isinstance(an, str) and an.strip():
                    label = an.strip()
                road = _as_mapping(first.get("road_address"))
                if road is not None:
                    rn = road.get("address_name")
                    if isinstance(rn, str) and rn.strip():
                        label = rn.strip()
                return lat, lng, label

    # Fallback: keyword place search on the road name
    url_kw = f"https://dapi.kakao.com/v2/local/search/keyword.json?{query}"
    data_kw = fetch(url_kw, _auth_headers(api_key))
    docs_kw = _as_sequence(data_kw.get("documents"))
    if not docs_kw:
        msg = f"Could not geocode anchor: {address}"
        raise RuntimeError(msg)
    first_kw = _as_mapping(docs_kw[0])
    if first_kw is None:
        msg = "Invalid keyword geocode document"
        raise RuntimeError(msg)
    lat = _as_float(first_kw.get("y"))
    lng = _as_float(first_kw.get("x"))
    if lat is None or lng is None:
        msg = "Keyword geocode missing coordinates"
        raise RuntimeError(msg)
    label = str(first_kw.get("road_address_name") or first_kw.get("address_name") or address)
    return lat, lng, label


def _paginate_category(
    *,
    lat: float,
    lng: float,
    category_code: str,
    radius_m: int,
    api_key: str,
    fetch: JsonFetch,
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for page in range(1, _MAX_PAGES + 1):
        query = urllib.parse.urlencode(
            {
                "category_group_code": category_code,
                "x": f"{lng}",
                "y": f"{lat}",
                "radius": str(radius_m),
                "size": "15",
                "page": str(page),
                "sort": "distance",
            },
        )
        url = f"https://dapi.kakao.com/v2/local/search/category.json?{query}"
        data = fetch(url, _auth_headers(api_key))
        docs = _as_sequence(data.get("documents"))
        meta = _as_mapping(data.get("meta")) or {}
        if not docs:
            break
        for item in docs:
            mapped = _as_mapping(item)
            if mapped is not None:
                out.append(dict(mapped))
        if bool(meta.get("is_end")):
            break
    return out


def _paginate_keyword(
    *,
    lat: float,
    lng: float,
    query_text: str,
    radius_m: int,
    api_key: str,
    fetch: JsonFetch,
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for page in range(1, _MAX_PAGES + 1):
        query = urllib.parse.urlencode(
            {
                "query": query_text,
                "x": f"{lng}",
                "y": f"{lat}",
                "radius": str(radius_m),
                "size": "15",
                "page": str(page),
                "sort": "distance",
            },
        )
        url = f"https://dapi.kakao.com/v2/local/search/keyword.json?{query}"
        data = fetch(url, _auth_headers(api_key))
        docs = _as_sequence(data.get("documents"))
        meta = _as_mapping(data.get("meta")) or {}
        if not docs:
            break
        for item in docs:
            mapped = _as_mapping(item)
            if mapped is not None:
                out.append(dict(mapped))
        if bool(meta.get("is_end")):
            break
    return out


def _doc_fields(doc: Mapping[str, object]) -> dict[str, object]:
    place_id = str(doc.get("id") or "")
    name = str(doc.get("place_name") or "").strip()
    road = str(doc.get("road_address_name") or "").strip()
    jibun = str(doc.get("address_name") or "").strip()
    cat = str(doc.get("category_name") or "").strip()
    phone = str(doc.get("phone") or "").strip()
    dist = _as_float(doc.get("distance"))
    lat = _as_float(doc.get("y"))
    lng = _as_float(doc.get("x"))
    return {
        "place_id": place_id,
        "name": name,
        "road": road,
        "jibun": jibun,
        "cat": cat,
        "phone": phone,
        "dist": dist if dist is not None else 0.0,
        "lat": lat,
        "lng": lng,
    }


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(m in text for m in markers)


def _classify_sm_ssm(name: str, category_name: str) -> StoreChannel | None:
    blob = f"{name} {category_name}"
    # Drop pure convenience / cafe noise
    if "편의점" in category_name or re.search(
        r"(GS25|CU|세븐일레븐|이마트24|미니스톱)",
        name,
    ):
        return None
    top = category_name.split(">")[0] if category_name else ""
    if ("카페" in category_name or "음식점" in top) and (
        "슈퍼" not in category_name and "마트" not in category_name
    ):
        return None
    if (
        _contains_any(blob, _HYPER_NAME_MARKERS)
        and "익스프레스" not in blob
        and "에브리데이" not in blob
        and "슈퍼" not in name
    ):
        return None
    if _contains_any(blob, _SSM_NAME_MARKERS):
        return "ssm"
    if "기업형" in blob or "SSM" in blob.upper():
        return "ssm"
    if "슈퍼" in blob or "마트" in category_name:
        return "supermarket"
    return None


def _classify_hyper(name: str, category_name: str) -> bool:
    blob = f"{name} {category_name}"
    if "익스프레스" in blob or "에브리데이" in blob or "더프레시" in blob:
        return False
    return "편의점" not in category_name


def _dong_from_address(road: str, jibun: str) -> str:
    text = jibun or road
    # Prefer "…구 …동" style
    pattern = (
        r"((?:서울|경기|인천|부산|대구|대전|광주|울산|세종)[^\s]*\s)?"
        + r"([가-힣]+시)?\s*([가-힣]+구)\s*([가-힣0-9]+동)"
    )
    m = re.search(pattern, text)
    if m:
        parts = [p for p in m.groups() if p]
        return " ".join(p.strip() for p in parts if p)
    # Goyang style without leading sido sometimes
    m2 = re.search(r"(고양시\s*덕양구)\s*([가-힣0-9]+동)", text)
    if m2:
        return f"경기도 {m2.group(1)} {m2.group(2)}".replace("  ", " ")
    if text:
        parts = text.split()
        return " ".join(parts[:4]) if parts else text
    return "경기도 고양시 덕양구"


def _infer_accessibility(name: str, road: str, category_name: str) -> str:
    blob = f"{name} {road} {category_name}".lower()
    indoor_keys = ("지하", "역사", "몰 ", "쇼핑몰", "터미널", "빌딩", "타워", "센터점")
    if any(k in blob for k in indoor_keys):
        return "indoor"
    road_keys = ("대로", "중앙로", "충장로", "호국로", "통일로", "고양대로")
    if any(k in road for k in road_keys):
        return "main_road"
    if re.search(r"번길|골목|이면", road):
        return "alley"
    return "main_road"


def _infer_trade_area(
    *,
    context_cats: list[str],
    context_names: list[str],
) -> tuple[str, list[str]]:
    """Heuristic trade_area from nearby Kakao categories/names."""
    notes: list[str] = []
    blob = " ".join(context_cats + context_names)
    score = {
        "office": 0,
        "residential": 0,
        "campus": 0,
        "tourist": 0,
        "suburban": 0,
    }
    if any(x in blob for x in ("지하철", "SW8", "공공기관", "은행", "오피스")):
        score["office"] += 2
        notes.append("대중교통·공공/업무 시설 근접")
    if any(x in blob for x in ("학교", "학원", "대학교", "SC4", "AC5")):
        score["campus"] += 2
        notes.append("교육시설 밀집")
    if any(x in blob for x in ("아파트", "주거", "마을", "단지")):
        score["residential"] += 2
        notes.append("주거 단지 키워드")
    if any(x in blob for x in ("관광", "문화시설", "백화점", "아울렛", "테마")):
        score["tourist"] += 2
        notes.append("집객·상업 앵커")
    # Goyang Deogyang / Haengsin is largely residential-suburban
    score["residential"] += 1
    score["suburban"] += 1
    best = max(score, key=lambda k: score[k])
    if score[best] <= 1:
        best = "residential"
        notes.append("기본 추정: 주거 밀착")
    return best, notes


def _channel_defaults(channel: StoreChannel) -> dict[str, ParameterValue]:
    if channel == "convenience":
        return {
            "store_type": "convenience",
            "store_size": "cv_s",
            "avg_ticket": "t_le_8k",
            "product_name": "냉장 간편식 도시락",
            "daily_demand": 12.0,
            "standard_lead_time_days": 1.5,
            "service_level": "sl_95",
        }
    if channel == "supermarket":
        return {
            "store_type": "supermarket",
            "store_size": "sm",
            "avg_ticket": "t_8k_15k",
            "product_name": "상온 라면",
            "daily_demand": 18.0,
            "standard_lead_time_days": 2.0,
            "service_level": "sl_95",
        }
    if channel == "ssm":
        return {
            "store_type": "ssm",
            "store_size": "ssm",
            "avg_ticket": "t_15k_25k",
            "product_name": "유제품 흰우유 1L",
            "daily_demand": 35.0,
            "standard_lead_time_days": 2.5,
            "service_level": "sl_95",
        }
    return {
        "store_type": "hypermarket",
        "store_size": "hyper",
        "avg_ticket": "t_45k_55k",
        "product_name": "생수 2L 6입",
        "daily_demand": 80.0,
        "standard_lead_time_days": 3.0,
        "service_level": "sl_95",
    }


def _context_scan(
    *,
    lat: float,
    lng: float,
    api_key: str,
    fetch: JsonFetch,
) -> tuple[float, list[str], list[str]]:
    """Lightweight nearby context for inference (single page per category)."""
    cats: list[str] = []
    names: list[str] = []
    for code in ("SW8", "SC4", "MT1", "CS2", "PO3"):
        try:
            query = urllib.parse.urlencode(
                {
                    "category_group_code": code,
                    "x": f"{lng}",
                    "y": f"{lat}",
                    "radius": str(CONTEXT_RADIUS_M),
                    "size": "10",
                    "page": "1",
                    "sort": "distance",
                },
            )
            url = f"https://dapi.kakao.com/v2/local/search/category.json?{query}"
            data = fetch(url, _auth_headers(api_key))
            docs = _as_sequence(data.get("documents")) or []
        except (urllib.error.URLError, TimeoutError, TypeError, RuntimeError, OSError):
            continue
        for item in list(docs)[:5]:
            doc = _as_mapping(item)
            if doc is None:
                continue
            name = str(doc.get("place_name") or "")
            cat = str(doc.get("category_name") or code)
            if name:
                names.append(name)
            cats.append(cat)
    # crude FTI proxy: more transit/school/mart → higher
    score = 0.0
    blob = " ".join(cats + names)
    if "지하철" in blob or "SW8" in blob:
        score += 0.35
    if "학교" in blob or "학원" in blob:
        score += 0.2
    if "마트" in blob:
        score += 0.15
    score += min(0.3, 0.02 * len(names))
    return round(min(1.0, score), 3), cats, names


def _build_store(
    *,
    fields: dict[str, object],
    channel: StoreChannel,
    api_key: str,
    fetch: JsonFetch,
    with_context: bool,
) -> SurveyedStore | None:
    name = str(fields["name"])
    if not name:
        return None
    place_id = str(fields.get("place_id") or name)
    road = str(fields.get("road") or "")
    jibun = str(fields.get("jibun") or "")
    dist_raw = fields.get("dist")
    dist = float(dist_raw) if isinstance(dist_raw, (int, float)) else 0.0
    lat = fields.get("lat")
    lng = fields.get("lng")
    lat_f = float(lat) if isinstance(lat, (int, float)) else None
    lng_f = float(lng) if isinstance(lng, (int, float)) else None

    defaults = _channel_defaults(channel)
    dong = _dong_from_address(road, jibun)
    access = _infer_accessibility(name, road, str(fields["cat"]))

    fti = 0.0
    notes: list[str] = []
    trade = "residential"
    if with_context and lat_f is not None and lng_f is not None:
        fti, cats, names = _context_scan(
            lat=lat_f,
            lng=lng_f,
            api_key=api_key,
            fetch=fetch,
        )
        trade, tnotes = _infer_trade_area(context_cats=cats, context_names=names)
        notes.extend(tnotes)
        if fti >= 0.4:
            notes.append(f"주변 유동 신호 중상 (proxy FTI≈{fti:.2f})")
        elif fti <= 0.15:
            notes.append(f"주변 유동 신호 낮음 (proxy FTI≈{fti:.2f})")

    notes.append(f"앵커 기준 직선거리 약 {dist:.0f}m")
    summary = (
        f"{name} · {channel} · {trade}/{access} · "
        f"FTI≈{fti:.2f} · {dong}"
    )

    return SurveyedStore(
        id=_stable_id(place_id, name, road or jibun),
        place_id=place_id,
        name=name,
        channel=channel,
        distance_m=round(dist, 1),
        road_address=road,
        jibun_address=jibun,
        address_display=road or jibun,
        category_name=str(fields["cat"]),
        lat=lat_f,
        lng=lng_f,
        phone=str(fields["phone"]),
        trade_area=trade,
        accessibility=access,
        store_size=str(defaults["store_size"]),
        avg_ticket=str(defaults["avg_ticket"]),
        location_dong=(
            dong
            if dong.startswith("경기도") or dong.startswith("서울")
            else f"경기도 {dong}"
        ),
        product_name=str(defaults["product_name"]),
        daily_demand=float(defaults["daily_demand"]),
        standard_lead_time_days=float(defaults["standard_lead_time_days"]),
        service_level=str(defaults["service_level"]),
        foot_traffic_index=fti,
        context_notes=notes,
        inference_summary=summary,
    )


def survey_anchor_stores(
    *,
    api_key: str | None,
    anchor_address: str = DEFAULT_ANCHOR_ADDRESS,
    fetch: JsonFetch | None = None,
    with_context: bool = True,
    max_context_stores: int = 24,
) -> AnchorSurveyResult:
    """Live Kakao census around the demo anchor."""
    from datetime import UTC, datetime

    notes: list[str] = []
    if not api_key:
        snap = load_survey_snapshot()
        if snap is not None:
            snap.notes = [*snap.notes, "Kakao key 없음 — 스냅샷 사용"]
            snap.used_live_api = False
            return snap
        return AnchorSurveyResult(
            anchor_address=anchor_address,
            notes=["Kakao REST API key 없음 · 스냅샷도 없음"],
            used_live_api=False,
        )

    fetch_fn = fetch or _http_get_json
    try:
        lat, lng, label = _geocode(anchor_address, api_key=api_key, fetch=fetch_fn)
    except (urllib.error.URLError, TimeoutError, TypeError, RuntimeError, OSError) as exc:
        logger.warning("anchor geocode failed: %s", exc)
        snap = load_survey_snapshot()
        if snap is not None:
            snap.notes = [*snap.notes, f"라이브 geocode 실패: {exc}"]
            return snap
        return AnchorSurveyResult(
            anchor_address=anchor_address,
            notes=[f"geocode 실패: {exc}"],
            used_live_api=False,
        )

    raw_by_id: dict[str, tuple[StoreChannel, dict[str, object]]] = {}

    # 1) Convenience CS2 within 1km (reclassify obvious marts mis-tagged as CS2)
    for doc in _paginate_category(
        lat=lat,
        lng=lng,
        category_code="CS2",
        radius_m=RADIUS_CONVENIENCE_M,
        api_key=api_key,
        fetch=fetch_fn,
    ):
        f = _doc_fields(doc)
        pid = str(f.get("place_id") or f.get("name") or "")
        dist_v = f.get("dist")
        dist = float(dist_v) if isinstance(dist_v, (int, float)) else 0.0
        if dist > RADIUS_CONVENIENCE_M:
            continue
        name = str(f.get("name") or "")
        cat = str(f.get("cat") or "")
        sm_ch = _classify_sm_ssm(name, cat)
        if sm_ch is not None and not re.search(
            r"(GS25|CU|세븐일레븐|이마트24|미니스톱|씨유)",
            name,
        ):
            raw_by_id[pid] = (sm_ch, f)
        else:
            raw_by_id[pid] = ("convenience", f)

    # 2) Hyper MT1 within 10km
    for doc in _paginate_category(
        lat=lat,
        lng=lng,
        category_code="MT1",
        radius_m=RADIUS_HYPER_M,
        api_key=api_key,
        fetch=fetch_fn,
    ):
        f = _doc_fields(doc)
        pid = str(f.get("place_id") or f.get("name") or "")
        if not _classify_hyper(str(f.get("name") or ""), str(f.get("cat") or "")):
            continue
        dist_v = f.get("dist")
        dist = float(dist_v) if isinstance(dist_v, (int, float)) else 0.0
        if dist > RADIUS_HYPER_M:
            continue
        raw_by_id[pid] = ("hypermarket", f)

    # 3) SM / SSM keywords within 3km
    for qtext in _SM_KEYWORD_QUERIES:
        for doc in _paginate_keyword(
            lat=lat,
            lng=lng,
            query_text=qtext,
            radius_m=RADIUS_SM_SSM_M,
            api_key=api_key,
            fetch=fetch_fn,
        ):
            f = _doc_fields(doc)
            pid = str(f.get("place_id") or f.get("name") or "")
            dist_v = f.get("dist")
            dist = float(dist_v) if isinstance(dist_v, (int, float)) else 0.0
            if dist > RADIUS_SM_SSM_M:
                continue
            # do not overwrite convenience/hyper already set
            if pid in raw_by_id and raw_by_id[pid][0] in ("convenience", "hypermarket"):
                continue
            channel = _classify_sm_ssm(str(f.get("name") or ""), str(f.get("cat") or ""))
            if channel is None:
                continue
            raw_by_id[pid] = (channel, f)

    def _dist_key(item: tuple[str, tuple[StoreChannel, dict[str, object]]]) -> float:
        dist_v = item[1][1].get("dist")
        return float(dist_v) if isinstance(dist_v, (int, float)) else 0.0

    # Sort by distance; run context only for nearest max_context_stores
    ordered = sorted(raw_by_id.items(), key=_dist_key)
    stores: list[SurveyedStore] = []
    for idx, (_pid, (channel, fields)) in enumerate(ordered):
        use_ctx = with_context and idx < max_context_stores
        store = _build_store(
            fields=fields,
            channel=channel,
            api_key=api_key,
            fetch=fetch_fn,
            with_context=use_ctx,
        )
        if store is not None:
            stores.append(store)

    counts: dict[str, int] = {}
    for s in stores:
        counts[s.channel] = counts.get(s.channel, 0) + 1

    notes.append(
        f"앵커 {label} ({lat:.5f},{lng:.5f}) 기준 "
        + f"CVS≤{RADIUS_CONVENIENCE_M}m · SM/SSM≤{RADIUS_SM_SSM_M}m · "
        + f"대형≤{RADIUS_HYPER_M}m 전수조사",
    )
    notes.append(f"총 {len(stores)}개 점포 · 채널별 {counts}")

    return AnchorSurveyResult(
        anchor_address=anchor_address,
        anchor_lat=lat,
        anchor_lng=lng,
        anchor_label=label,
        surveyed_at=datetime.now(UTC).isoformat(),
        provider="kakao",
        used_live_api=True,
        notes=notes,
        counts=counts,
        stores=stores,
    )


def save_survey_snapshot(result: AnchorSurveyResult, path: Path | None = None) -> Path:
    target = path or _SNAPSHOT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return target


def load_survey_snapshot(path: Path | None = None) -> AnchorSurveyResult | None:
    # 1) Embedded blob (top-level import keeps Vercel bundler packing it)
    if path is None and _EMBEDDED_SNAPSHOT_JSON:
        try:
            data = json.loads(_EMBEDDED_SNAPSHOT_JSON)
            return AnchorSurveyResult.model_validate(data)
        except Exception as exc:  # noqa: BLE001 — fallback to file paths
            logger.warning("embedded census snapshot load failed: %s", exc)

    candidates = [path] if path is not None else _snapshot_candidates()
    for target in candidates:
        if target is None or not target.is_file():
            continue
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return AnchorSurveyResult.model_validate(data)
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("survey snapshot load failed (%s): %s", target, exc)
    return None


def surveyed_store_to_parameters(store: SurveyedStore) -> dict[str, ParameterValue]:
    """Map a surveyed store into evaluate() parameters."""
    addr = store.road_address or store.jibun_address or store.address_display
    use_precise = bool(addr)
    return {
        "product_name": store.product_name,
        "store_type": store.channel if store.channel != "ssm" else "ssm",
        "store_size": store.store_size,
        "avg_ticket": store.avg_ticket,
        "location_dong": store.location_dong,
        "use_precise_location": use_precise,
        "store_address": addr if use_precise else "",
        "consider_temp_foot_traffic": False,
        "consider_competition_saturation": store.channel == "convenience",
        "trade_area": store.trade_area,
        "accessibility": store.accessibility,
        "daily_demand": store.daily_demand,
        "standard_lead_time_days": store.standard_lead_time_days,
        "service_level": store.service_level,
        "order_day_pattern": "auto",
    }


def surveyed_to_demo_cards(result: AnchorSurveyResult) -> list[dict[str, object]]:
    """UI-oriented cards for verified demo list."""
    cards: list[dict[str, object]] = []
    channel_ko = {
        "convenience": "편의점",
        "supermarket": "일반 슈퍼",
        "ssm": "기업형 슈퍼(SSM)",
        "hypermarket": "대형마트·할인점",
    }
    for store in result.stores:
        params = surveyed_store_to_parameters(store)
        radius_label = {
            "convenience": "1km",
            "supermarket": "3km",
            "ssm": "3km",
            "hypermarket": "10km",
        }[store.channel]
        cards.append(
            {
                "id": store.id,
                "tier": "verified",
                "title": f"{store.name}",
                "storeLabel": (
                    f"{channel_ko[store.channel]} · 앵커 {store.distance_m:.0f}m "
                    f"(조사 반경 {radius_label}) · {store.accessibility}"
                ),
                "blurb": store.inference_summary,
                "highlight": (
                    f"{channel_ko[store.channel]} · {store.trade_area} · "
                    f"FTI≈{store.foot_traffic_index:.2f} · "
                    f"{store.product_name} D={store.daily_demand:g}"
                ),
                "verificationNote": (
                    "앵커 주소 전수조사(Kakao) · "
                    + (
                        " · ".join(store.context_notes[:3])
                        if store.context_notes
                        else "입지 추론"
                    )
                ),
                "expected": {},
                "parameters": params,
                "channel": store.channel,
                "distance_m": store.distance_m,
                "foot_traffic_index": store.foot_traffic_index,
            },
        )
    return cards
