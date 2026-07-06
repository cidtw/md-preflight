from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class SourceStatus(StrEnum):
    AVAILABLE = "available"
    PLANNED = "planned"


class SourceMeta(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: str
    label: str
    description: str
    auth_fields: list[str]
    status: SourceStatus
