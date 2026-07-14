from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class RoleScoreItem(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    role: str
    score: float
    matched_columns: list[str] = Field(default_factory=list)
    missing_columns: list[str] = Field(default_factory=list)


class ArtifactRoleSuggestion(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    artifact_id: str
    filename: str
    headers: list[str] = Field(default_factory=list)
    suggested_role: str | None = None
    assigned_role: str | None = None
    confidence: float = 0.0
    scores: list[RoleScoreItem] = Field(default_factory=list)


class DetectRolesResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    artifacts: list[ArtifactRoleSuggestion] = Field(default_factory=list)
    frames_ready: dict[str, bool] = Field(default_factory=dict)
