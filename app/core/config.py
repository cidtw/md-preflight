"""Slim application settings for the redesign skeleton."""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="MDPREFLIGHT_",
        extra="ignore",
    )

    app_name: str = "MD Preflight Pipeline"
    app_version: str = "0.2.0-redesign"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
