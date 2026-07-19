"""Thin HTTP adapter over the ROP pipeline."""

from __future__ import annotations

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
)
from app.schemas.evaluate import EvaluateRequest, EvaluateResponse
from app.schemas.places import DongSearchResponse, PlaceSearchResponse, SimulationResponse

router = APIRouter(prefix="/api", tags=["pipeline"])


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_app_settings)]) -> dict[str, str | int | bool]:
    from app.pipeline.demo_anchor_survey import load_survey_snapshot

    snap = load_survey_snapshot()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "pipeline": "input-analyze-output",
        "service": "rop-adjust",
        "census_snapshot_stores": len(snap.stores) if snap else 0,
        "census_live_key": bool(settings.kakao_rest_api_key),
    }


@router.get("/template", response_model=InputTemplate)
def read_template() -> InputTemplate:
    """Public input template for store-specific ROP adjustment."""
    return get_input_template()


@router.get("/demo/verified-stores", response_model=list[VerifiedDemoStore])
def demo_verified_stores(
    settings: Annotated[Settings, Depends(get_app_settings)],
    live: Annotated[bool, Query(description="Kakao 라이브 전수조사 사용")] = True,
) -> list[VerifiedDemoStore]:
    """Anchor census demo stores (세솔로 25 반경 전수조사 기반)."""
    _ = settings
    return list_verified_demo_stores(live=live)


@router.get("/demo/verified-stores/{store_id}", response_model=VerifiedDemoStore)
def demo_verified_store(store_id: str) -> VerifiedDemoStore:
    """One demo store by id (from live census or snapshot)."""
    store = get_verified_demo_store(store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown verified demo store: {store_id}",
        )
    return store


@router.get("/demo/survey-anchor", response_model=AnchorSurveyResult)
def demo_survey_anchor(
    settings: Annotated[Settings, Depends(get_app_settings)],
    address: Annotated[
        str,
        Query(description="전수조사 앵커 주소"),
    ] = DEFAULT_ANCHOR_ADDRESS,
    with_context: Annotated[bool, Query()] = True,
) -> AnchorSurveyResult:
    """Full retail census around the demo anchor via Kakao Local."""
    result = survey_anchor_stores(
        api_key=settings.kakao_rest_api_key,
        anchor_address=address.strip() or DEFAULT_ANCHOR_ADDRESS,
        with_context=with_context,
    )
    return result


@router.post("/demo/survey-anchor/refresh", response_model=AnchorSurveyResult)
def demo_survey_anchor_refresh(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AnchorSurveyResult:
    """Re-run census and attempt to write data/demo_anchor_survey.json (local only)."""
    result = survey_anchor_stores(
        api_key=settings.kakao_rest_api_key,
        anchor_address=DEFAULT_ANCHOR_ADDRESS,
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
