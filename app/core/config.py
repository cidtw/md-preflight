from functools import lru_cache
from typing import ClassVar, Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.rule_config import RuleThresholds

AuthMode = Literal["clerk", "stub", "off"]


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="MDPREFLIGHT_",
        extra="ignore",
    )

    llm_model: str = "claude-sonnet-5"
    openai_model: str = "gpt-5.5"
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "MDPREFLIGHT_DATABASE_URL"),
    )
    database_url_unpooled: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL_UNPOOLED", "MDPREFLIGHT_DATABASE_URL_UNPOOLED"),
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "MDPREFLIGHT_OPENAI_API_KEY"),
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "MDPREFLIGHT_ANTHROPIC_API_KEY"),
    )
    clerk_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CLERK_SECRET_KEY", "MDPREFLIGHT_CLERK_SECRET_KEY"),
    )
    clerk_publishable_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
            "CLERK_PUBLISHABLE_KEY",
            "MDPREFLIGHT_CLERK_PUBLISHABLE_KEY",
        ),
    )
    clerk_authorized_origins: tuple[str, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices(
            "CLERK_AUTHORIZED_ORIGINS",
            "CLERK_ALLOWED_ORIGINS",
            "MDPREFLIGHT_CLERK_AUTHORIZED_ORIGINS",
        ),
    )
    allow_stub_auth: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "MDPREFLIGHT_ALLOW_STUB_AUTH",
            "ALLOW_STUB_AUTH",
        ),
    )
    max_upload_bytes: int = 5 * 1024 * 1024
    allowed_extensions: tuple[str, ...] = (".csv", ".xlsx")
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )
    rule_thresholds: RuleThresholds = Field(default_factory=RuleThresholds)

    @property
    def auth_mode(self) -> AuthMode:
        if self.clerk_secret_key and self.clerk_publishable_key:
            return "clerk"
        if self.allow_stub_auth:
            return "stub"
        return "off"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
