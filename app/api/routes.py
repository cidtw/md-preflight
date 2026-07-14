import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from app.api.deps import (
    get_app_settings,
    get_current_user_id,
    get_history_store,
    get_narrative_generator,
    get_run_store,
)
from app.core.config import Settings
from app.core.errors import IngestError, UploadValidationError
from app.rules import RULES
from app.schemas.catalog import PreflightCatalog
from app.schemas.history import HistoryBucket, RunHistoryRecord
from app.schemas.report import PreflightReport
from app.schemas.rule_meta import RuleMeta
from app.schemas.source_meta import SourceMeta
from app.services.catalog_service import build_preflight_catalog
from app.services.history_store import HistoryGranularity, HistoryStore
from app.services.report_service import render_markdown_report
from app.services.run_store import RunStore
from app.services.validation_engine import UploadedFiles, build_uploaded_context, validate_context
from app.sources import SOURCE_CATALOG

router = APIRouter(prefix="/api/preflight", tags=["preflight"])
logger = logging.getLogger(__name__)


def build_report_download_filename(report: PreflightReport) -> str:
    timestamp = report.created_at.strftime("%Y-%m-%d-%H%M")
    return f"preflight-{timestamp}-report.md"


def _iter_uploads(files: UploadedFiles) -> tuple[UploadFile, UploadFile, UploadFile]:
    return files.promotion_plan, files.product_master, files.inventory


async def validate_uploaded_files(files: UploadedFiles, settings: Settings) -> None:
    for upload in _iter_uploads(files):
        filename = upload.filename or "upload"
        extension = Path(filename).suffix.lower()
        if extension not in settings.allowed_extensions:
            raise UploadValidationError(
                message=f"Unsupported file extension for {filename}: {extension or '<none>'}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        content = await upload.read()
        await upload.seek(0)
        if len(content) > settings.max_upload_bytes:
            raise UploadValidationError(
                message=f"Uploaded file exceeds size limit for {filename}",
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            )


async def build_report_from_uploads(
    *,
    files: UploadedFiles,
    run_store: RunStore,
    history_store: HistoryStore,
    settings: Settings,
    use_llm: bool,
    user_id: str | None,
) -> PreflightReport:
    await validate_uploaded_files(files, settings)
    context = await build_uploaded_context(files, settings.rule_thresholds)
    report = validate_context(
        context,
        generator=get_narrative_generator(settings=settings, use_llm=use_llm),
    )
    try:
        run_store.save(report, owner_user_id=user_id)
    except Exception:
        logger.exception("run persistence failed for run %s", report.run_id)
    if user_id is not None:
        try:
            history_store.append(RunHistoryRecord.from_report(user_id, report.run_id, report))
        except Exception:
            logger.exception("history persistence failed for run %s", report.run_id)
    return report


@router.post("", response_model=PreflightReport)
async def preflight_files(
    promotion_plan: Annotated[UploadFile, File()],
    product_master: Annotated[UploadFile, File()],
    inventory: Annotated[UploadFile, File()],
    run_store: Annotated[RunStore, Depends(get_run_store)],
    history_store: Annotated[HistoryStore, Depends(get_history_store)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    use_llm: Annotated[bool, Form()] = True,
) -> PreflightReport:
    files = UploadedFiles(
        promotion_plan=promotion_plan,
        product_master=product_master,
        inventory=inventory,
    )
    try:
        return await build_report_from_uploads(
            files=files,
            run_store=run_store,
            history_store=history_store,
            settings=settings,
            use_llm=use_llm,
            user_id=user_id,
        )
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from None
    except IngestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from None


@router.post("/validate", response_model=PreflightReport)
async def validate_files(
    promotion_plan: Annotated[UploadFile, File()],
    product_master: Annotated[UploadFile, File()],
    inventory: Annotated[UploadFile, File()],
    run_store: Annotated[RunStore, Depends(get_run_store)],
    history_store: Annotated[HistoryStore, Depends(get_history_store)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    user_id: Annotated[str | None, Depends(get_current_user_id)],
) -> PreflightReport:
    files = UploadedFiles(
        promotion_plan=promotion_plan,
        product_master=product_master,
        inventory=inventory,
    )
    try:
        return await build_report_from_uploads(
            files=files,
            run_store=run_store,
            history_store=history_store,
            settings=settings,
            use_llm=False,
            user_id=user_id,
        )
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from None
    except IngestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from None


def authorize_run_access(
    *,
    run_store: RunStore,
    run_id: str,
    user_id: str | None,
) -> PreflightReport:
    stored = run_store.get_stored(run_id)
    if stored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    # owner_user_id is None for runs created without a signed-in user: the run_id
    # itself (a uuid4 hex) is the unguessable capability token for those.
    if stored.owner_user_id is not None:
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login required to view this run",
            )
        if user_id != stored.owner_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this run",
            )
    return stored.report


@router.get("/runs/{run_id}", response_model=PreflightReport)
def get_run(
    run_id: str,
    run_store: Annotated[RunStore, Depends(get_run_store)],
    user_id: Annotated[str | None, Depends(get_current_user_id)],
) -> PreflightReport:
    return authorize_run_access(run_store=run_store, run_id=run_id, user_id=user_id)


@router.get("/runs/{run_id}/report.md")
def download_markdown_report(
    run_id: str,
    run_store: Annotated[RunStore, Depends(get_run_store)],
    user_id: Annotated[str | None, Depends(get_current_user_id)],
) -> Response:
    report = authorize_run_access(run_store=run_store, run_id=run_id, user_id=user_id)
    return Response(
        content=render_markdown_report(report),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{build_report_download_filename(report)}"'
            ),
        },
    )


@router.get("/rules", response_model=list[RuleMeta])
def get_rules() -> list[RuleMeta]:
    return [rule.meta() for rule in RULES]


@router.get("/catalog", response_model=PreflightCatalog)
def get_catalog(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> PreflightCatalog:
    """Read-only thresholds + column aliases + rules for Settings (T53)."""
    return build_preflight_catalog(settings)


@router.get("/sources", response_model=list[SourceMeta])
def get_sources() -> list[SourceMeta]:
    return SOURCE_CATALOG


@router.get("/history", response_model=list[HistoryBucket])
def get_history(
    history_store: Annotated[HistoryStore, Depends(get_history_store)],
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    granularity: Annotated[HistoryGranularity, Query()] = "day",
) -> list[HistoryBucket]:
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required for history dashboard",
        )
    return history_store.query(user_id, granularity)


@router.get("/history/runs", response_model=list[RunHistoryRecord])
def get_history_runs(
    history_store: Annotated[HistoryStore, Depends(get_history_store)],
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[RunHistoryRecord]:
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required for history dashboard",
        )
    return history_store.list_runs(user_id, limit=limit)


@router.get("/health")
def health(
    settings: Annotated[Settings, Depends(get_app_settings)],
    run_store: Annotated[RunStore, Depends(get_run_store)],
    history_store: Annotated[HistoryStore, Depends(get_history_store)],
) -> dict[str, str]:
    run_backend = "postgres" if type(run_store).__name__ == "PostgresRunStore" else "in_memory"
    history_backend = (
        "postgres" if type(history_store).__name__ == "PostgresHistoryStore" else "in_memory"
    )
    return {
        "status": "ok",
        "auth_mode": settings.auth_mode,
        "run_backend": run_backend,
        "history_backend": history_backend,
    }
