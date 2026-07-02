from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from app.schemas.issue import Severity


class RuleMeta(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    code: str
    severity: Severity
    description: str
