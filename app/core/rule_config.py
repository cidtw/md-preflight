from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class RuleThresholds(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    max_discount_rate: float = Field(default=0.7, ge=0.0, le=1.0)
    min_margin_rate: float = Field(default=0.05, ge=0.0, le=1.0)
