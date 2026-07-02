from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_app_settings, get_run_store
from app.core.config import Settings
from app.core.errors import IngestError
from app.rules import RULES
from app.schemas.report import PreflightReport
from app.schemas.rule_meta import RuleMeta
from app.services.run_store import RunStore
from app.services.validation_engine import UploadedFiles, build_uploaded_context, validate_context

router = APIRouter(prefix="/api/preflight", tags=["preflight"])


@router.post("/validate", response_model=PreflightReport)
async def validate_files(
    promotion_plan: Annotated[UploadFile, File()],
    product_master: Annotated[UploadFile, File()],
    inventory: Annotated[UploadFile, File()],
    run_store: Annotated[RunStore, Depends(get_run_store)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> PreflightReport:
    try:
        context = await build_uploaded_context(
            UploadedFiles(
                promotion_plan=promotion_plan,
                product_master=product_master,
                inventory=inventory,
            ),
            settings.rule_thresholds,
        )
        report = validate_context(context)
    except IngestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
    run_store.save(report)
    return report


@router.get("/runs/{run_id}", response_model=PreflightReport)
def get_run(
    run_id: str,
    run_store: Annotated[RunStore, Depends(get_run_store)],
) -> PreflightReport:
    report = run_store.get(run_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return report


@router.get("/rules", response_model=list[RuleMeta])
def get_rules() -> list[RuleMeta]:
    return [rule.meta() for rule in RULES]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
