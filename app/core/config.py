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
    app_version: str = "0.3.6-rop"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "https://md-preflight.vercel.app",
        ],
    )
    kakao_rest_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "KAKAO_REST_API_KEY",
            "MDPREFLIGHT_KAKAO_REST_API_KEY",
        ),
    )
    geo_radius_m: int = Field(default=500, ge=50, le=20000)
    # SpaceXAI / xAI — sales-decline response plan (server-side only).
    xai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "XAI_API_KEY",
            "MDPREFLIGHT_XAI_API_KEY",
        ),
    )
    xai_model: str = Field(
        default="grok-4.5",
        validation_alias=AliasChoices(
            "XAI_MODEL",
            "MDPREFLIGHT_XAI_MODEL",
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
