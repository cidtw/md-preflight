from functools import lru_cache
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.rule_config import RuleThresholds


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_prefix="MDPREFLIGHT_",
    )

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )
    rule_thresholds: RuleThresholds = Field(default_factory=RuleThresholds)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
