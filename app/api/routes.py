"""Thin HTTP adapter over the ROP pipeline."""

from __future__ import annotations

import re
import time
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.core.errors import InputValidationError
from app.pipeline import get_input_template, run
from app.pipeline.analyze.competition_sim import SimulationRequest, run_simulation
from app.pipeline.analyze.store_search import search_dong, search_places
from app.pipeline.demo_anchor_survey import (
    DEFAULT_ANCHOR_ADDRESS,
    AnchorSurveyResult,
    save_survey_snapshot,
    survey_anchor_stores,
)
from app.pipeline.region_catalog import list_sido, list_sigungu
from app.pipeline.types import InputTemplate
from app.pipeline.verified_demo_stores import (
    VerifiedDemoStore,
    get_verified_demo_store,
    list_verified_demo_stores,
    stores_from_survey_result,
)
from app.schemas.evaluate import EvaluateRequest, EvaluateResponse
from app.schemas.places import DongSearchResponse, PlaceSearchResponse, SimulationResponse

router = APIRouter(prefix="/api", tags=["pipeline"])

# --- Demo census guardrails (unauthenticated high-cost Kakao paths) ---
_SURVEY_LOCK = Lock()
# key -> (expires_at_monotonic, result)
_SURVEY_CACHE: dict[str, tuple[float, AnchorSurveyResult]] = {}
_SURVEY_CACHE_TTL_S = 3600.0
_SURVEY_MIN_INTERVAL_S = 60.0
_SURVEY_LAST_CALL: dict[str, float] = {}

_ALLOWED_SURVEY_ANCHORS = frozenset(
    {
        re.sub(r"\s+", "", DEFAULT_ANCHOR_ADDRESS),
        re.sub(r"\s+", "", "경기 고양시 덕양구 세솔로 25"),
        re.sub(r"\s+", "", "경기도 고양시 덕양구 세솔로 25"),
    },
)


def _anchor_key(address: str) -> str:
    return re.sub(r"\s+", "", (address or "").strip())


def _is_allowed_survey_anchor(address: str) -> bool:
    key = _anchor_key(address)
    if key in _ALLOWED_SURVEY_ANCHORS:
        return True
    # Accept only the demo home road name (prevents arbitrary address abuse).
    return key.endswith("세솔로25") and ("고양" in key or "덕양" in key)


def _cached_survey(address: str, with_context: bool) -> AnchorSurveyResult | None:
    cache_key = f"{_anchor_key(address)}|{int(with_context)}"
    hit = _SURVEY_CACHE.get(cache_key)
    if hit is None:
        return None
    expires_at, result = hit
    if time.monotonic() > expires_at:
        _ = _SURVEY_CACHE.pop(cache_key, None)
        return None
    return result


def _store_survey_cache(
    address: str,
    with_context: bool,
    result: AnchorSurveyResult,
) -> None:
    cache_key = f"{_anchor_key(address)}|{int(with_context)}"
    _SURVEY_CACHE[cache_key] = (time.monotonic() + _SURVEY_CACHE_TTL_S, result)


def _run_guarded_survey(
    *,
    api_key: str | None,
    address: str,
    with_context: bool,
) -> AnchorSurveyResult:
    """Whitelist + process cache + min interval for live Kakao census."""
    addr = (address or DEFAULT_ANCHOR_ADDRESS).strip() or DEFAULT_ANCHOR_ADDRESS
    if not _is_allowed_survey_anchor(addr):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Live census is limited to the demo anchor address "
                f"({DEFAULT_ANCHOR_ADDRESS}). Use the bundled snapshot via "
                "/api/demo/verified-stores instead."
            ),
        )

    cached = _cached_survey(addr, with_context)
    if cached is not None:
        notes = [*cached.notes, "process cache hit (TTL 1h)"]
        return cached.model_copy(update={"notes": notes, "used_live_api": False})

    cache_key = _anchor_key(addr)
    with _SURVEY_LOCK:
        # Double-check cache under lock
        cached2 = _cached_survey(addr, with_context)
        if cached2 is not None:
            notes = [*cached2.notes, "process cache hit (TTL 1h)"]
            return cached2.model_copy(update={"notes": notes, "used_live_api": False})

        last = _SURVEY_LAST_CALL.get(cache_key, 0.0)
        now = time.monotonic()
        if now - last < _SURVEY_MIN_INTERVAL_S:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Census rate limit: wait "
                    f"{int(_SURVEY_MIN_INTERVAL_S - (now - last))}s "
                    "or use /api/demo/verified-stores?live=false (snapshot)."
                ),
            )
        _SURVEY_LAST_CALL[cache_key] = now
        result = survey_anchor_stores(
            api_key=api_key,
            anchor_address=addr,
            with_context=with_context,
        )
        if result.stores:
            _store_survey_cache(addr, with_context, result)
        return result


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_app_settings)]) -> dict[str, str | int]:
    from app.pipeline.demo_anchor_survey import load_survey_snapshot

    snap = load_survey_snapshot()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "pipeline": "input-analyze-output",
        "service": "rop-adjust",
        "census_snapshot_stores": len(snap.stores) if snap else 0,
    }


@router.get("/template", response_model=InputTemplate)
def read_template() -> InputTemplate:
    """Public input template for store-specific ROP adjustment."""
    return get_input_template()


@router.get("/demo/verified-stores", response_model=list[VerifiedDemoStore])
def demo_verified_stores(
    settings: Annotated[Settings, Depends(get_app_settings)],
    live: Annotated[
        bool,
        Query(description="Kakao 라이브 전수조사 (기본 false · 스냅샷 사용)"),
    ] = False,
) -> list[VerifiedDemoStore]:
    """Demo stores from Sesol-ro 25 census snapshot (fast default)."""
    if live:
        # Live path still allowed but guarded (expensive, cached).
        result = _run_guarded_survey(
            api_key=settings.kakao_rest_api_key,
            address=DEFAULT_ANCHOR_ADDRESS,
            with_context=True,
        )
        cards = stores_from_survey_result(result)
        return cards if cards else list_verified_demo_stores(live=False)
    return list_verified_demo_stores(live=False)


@router.get("/demo/verified-stores/{store_id}", response_model=VerifiedDemoStore)
def demo_verified_store(store_id: str) -> VerifiedDemoStore:
    """One demo store by id (from snapshot)."""
    store = get_verified_demo_store(store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown verified demo store: {store_id}",
        )
    return store


@router.get(
    "/demo/survey-anchor",
    response_model=AnchorSurveyResult,
    include_in_schema=False,
)
def demo_survey_anchor(
    settings: Annotated[Settings, Depends(get_app_settings)],
    address: Annotated[
        str,
        Query(description="전수조사 앵커 (화이트리스트 전용)"),
    ] = DEFAULT_ANCHOR_ADDRESS,
    with_context: Annotated[bool, Query()] = True,
) -> AnchorSurveyResult:
    """Live Kakao census — whitelist + cache + rate limit (hidden from OpenAPI)."""
    return _run_guarded_survey(
        api_key=settings.kakao_rest_api_key,
        address=address,
        with_context=with_context,
    )


@router.post(
    "/demo/survey-anchor/refresh",
    response_model=AnchorSurveyResult,
    include_in_schema=False,
)
def demo_survey_anchor_refresh(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AnchorSurveyResult:
    """Re-run demo-anchor census only (local snapshot write best-effort)."""
    result = _run_guarded_survey(
        api_key=settings.kakao_rest_api_key,
        address=DEFAULT_ANCHOR_ADDRESS,
        with_context=True,
    )
    if result.used_live_api and result.stores:
        try:
            _ = save_survey_snapshot(result)
            result.notes = [*result.notes, "snapshot written to data/demo_anchor_survey.json"]
        except OSError as exc:
            result.notes = [*result.notes, f"snapshot write skipped: {exc}"]
    return result


@router.get("/regions/sido")
def regions_sido() -> dict[str, object]:
    """List top-level administrative divisions."""
    return {"items": list_sido()}


@router.get("/regions/sigungu")
def regions_sigungu(
    sido: Annotated[str, Query(min_length=1, description="시·도")],
) -> dict[str, object]:
    """List si/gun/gu under a sido."""
    return {"sido": sido, "items": list_sigungu(sido)}


@router.get("/regions/dong", response_model=DongSearchResponse)
def regions_dong(
    settings: Annotated[Settings, Depends(get_app_settings)],
    sido: Annotated[str, Query(min_length=1)],
    sigungu: Annotated[str, Query(min_length=1)],
    q: Annotated[str, Query(description="읍·면·동 부분 문자열")] = "",
) -> DongSearchResponse:
    """Suggest eup/myeon/dong/ri via Kakao address search."""
    return search_dong(
        api_key=settings.kakao_rest_api_key,
        sido=sido,
        sigungu=sigungu,
        q=q,
    )


@router.get("/places/search", response_model=PlaceSearchResponse)
def places_search(
    settings: Annotated[Settings, Depends(get_app_settings)],
    q: Annotated[str, Query(description="점포명·도로명·지번 일부")] = "",
    sido: Annotated[str, Query()] = "",
    sigungu: Annotated[str, Query()] = "",
    dong: Annotated[str, Query()] = "",
    store_type: Annotated[str, Query()] = "",
) -> PlaceSearchResponse:
    """Autocomplete store/address candidates (Kakao Local keyword + address)."""
    return search_places(
        q,
        api_key=settings.kakao_rest_api_key,
        sido=sido,
        sigungu=sigungu,
        dong=dong,
        store_type=store_type,
    )


@router.post("/simulate", response_model=SimulationResponse)
def simulate(body: SimulationRequest) -> SimulationResponse:
    """Competition / ops what-if simulation (deterministic parameter shocks)."""
    try:
        return run_simulation(body)
    except InputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from None
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter set: missing {exc}",
        ) from None


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(body: EvaluateRequest) -> EvaluateResponse:
    """Run input → internal calc → ROP report."""
    try:
        result = run(body.parameters)
    except InputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from None
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter set: missing {exc}",
        ) from None
    return EvaluateResponse.model_validate(result.model_dump())
