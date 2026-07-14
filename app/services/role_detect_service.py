"""Build detect-roles API payloads from uploaded tables (T57/T58)."""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import UploadValidationError
from app.domain.columns import SourceFile
from app.domain.role_detect import assign_roles_greedy, suggest_role
from app.ingest.loader import expand_upload_tables
from app.schemas.role_detect import (
    ArtifactRoleSuggestion,
    DetectRolesResponse,
    RoleScoreItem,
)
from app.services.validation_engine import read_upload


async def detect_roles_from_uploads(
    uploads: list[UploadFile],
    settings: Settings,
) -> DetectRolesResponse:
    if not uploads:
        return DetectRolesResponse(
            artifacts=[],
            frames_ready={role.value: False for role in SourceFile},
        )

    # (artifact_id, label, source_filename, sheet_name, headers)
    parsed: list[tuple[str, str, str, str | None, list[str]]] = []
    artifact_index = 0
    for upload_index, upload in enumerate(uploads):
        filename = upload.filename or f"upload-{upload_index}"
        extension = Path(filename).suffix.lower()
        if extension not in settings.allowed_extensions:
            raise UploadValidationError(
                message=(
                    f"Unsupported file extension for {filename}: "
                    f"{extension or '<none>'}"
                ),
                status_code=400,
            )
        name, content = await read_upload(upload)
        if len(content) > settings.max_upload_bytes:
            raise UploadValidationError(
                message=f"Uploaded file exceeds size limit for {filename}",
                status_code=413,
            )
        source_name = name or filename
        tables = expand_upload_tables(source_name, content)
        for table in tables:
            artifact_id = f"a{artifact_index}"
            artifact_index += 1
            parsed.append(
                (
                    artifact_id,
                    table.label,
                    table.source_filename,
                    table.sheet_name,
                    table.headers,
                )
            )

    greedy = assign_roles_greedy(
        [(artifact_id, headers) for artifact_id, _label, _src, _sheet, headers in parsed]
    )

    artifacts: list[ArtifactRoleSuggestion] = []
    for artifact_id, label, source_filename, sheet_name, headers in parsed:
        suggestion = suggest_role(headers)
        assigned = greedy.get(artifact_id)
        scores = [
            RoleScoreItem(
                role=item.role.value,
                score=item.score,
                matched_columns=list(item.matched_columns),
                missing_columns=list(item.missing_columns),
            )
            for item in suggestion.scores
        ]
        artifacts.append(
            ArtifactRoleSuggestion(
                artifact_id=artifact_id,
                filename=label,
                source_filename=source_filename,
                sheet_name=sheet_name,
                headers=headers,
                suggested_role=(
                    suggestion.suggested_role.value if suggestion.suggested_role else None
                ),
                assigned_role=assigned.value if assigned else None,
                confidence=suggestion.confidence,
                scores=scores,
            )
        )

    frames_ready = {role.value: False for role in SourceFile}
    for item in artifacts:
        if item.assigned_role:
            frames_ready[item.assigned_role] = True

    return DetectRolesResponse(artifacts=artifacts, frames_ready=frames_ready)
