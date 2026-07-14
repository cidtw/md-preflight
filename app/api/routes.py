"""Thin HTTP adapter over the three-stage pipeline."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.core.errors import InputValidationError
from app.pipeline import get_input_template, run
from app.pipeline.types import InputTemplate
from app.schemas.evaluate import EvaluateRequest, EvaluateResponse

router = APIRouter(prefix="/api", tags=["pipeline"])


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_app_settings)]) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "pipeline": "input-analyze-output",
    }


@router.get("/template", response_model=InputTemplate)
def read_template() -> InputTemplate:
    """Public input template — clients only send listed parameters."""
    return get_input_template()


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(body: EvaluateRequest) -> EvaluateResponse:
    """Run input → analyze → output and return a one-line recommendation."""
    try:
        result = run(body.parameters)
    except InputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from None
    return EvaluateResponse.model_validate(result.model_dump())
