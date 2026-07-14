"""Application settings for the ROP redesign service."""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="MDPREFLIGHT_",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "MD Preflight ROP"
    app_version: str = "0.3.1-rop"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
    )
    google_maps_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GOOGLE_MAPS_API_KEY",
            "MDPREFLIGHT_GOOGLE_MAPS_API_KEY",
        ),
    )
    geo_radius_m: int = Field(default=500, ge=50, le=5000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
