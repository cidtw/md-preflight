from __future__ import annotations

import os

from anthropic import Anthropic
from fastapi import Request
from openai import OpenAI

from app.core.config import Settings, get_settings
from app.services.clerk_auth import ClerkAuthenticationError, verify_clerk_session_token
from app.services.history_store import HISTORY_STORE as DEFAULT_HISTORY_STORE
from app.services.history_store import HistoryStore, build_history_store
from app.services.llm_service import (
    FallbackNarrativeGenerator,
    FallbackOnErrorNarrativeGenerator,
    LLMNarrativeGenerator,
    NarrativeGenerator,
    OpenAINarrativeGenerator,
)
from app.services.run_store import RUN_STORE, RunStore

_history_store_initialized = False
history_store_instance: HistoryStore = DEFAULT_HISTORY_STORE


def get_run_store() -> RunStore:
    return RUN_STORE


def get_history_store() -> HistoryStore:
    global history_store_instance, _history_store_initialized
    if not _history_store_initialized:
        if type(history_store_instance).__name__ == "InMemoryHistoryStore":
            history_store_instance = build_history_store()
        _history_store_initialized = True
    return history_store_instance


def get_app_settings() -> Settings:
    return get_settings()


def get_narrative_generator(*, settings: Settings, use_llm: bool) -> NarrativeGenerator:
    if not use_llm:
        return FallbackNarrativeGenerator()

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key:
        return FallbackOnErrorNarrativeGenerator(
            primary=OpenAINarrativeGenerator(
                client=OpenAI(api_key=openai_api_key),
                model=settings.openai_model,
            ),
            fallback=FallbackNarrativeGenerator(),
        )

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        return FallbackNarrativeGenerator()

    return FallbackOnErrorNarrativeGenerator(
        primary=LLMNarrativeGenerator(
            client=Anthropic(api_key=anthropic_api_key),
            model=settings.llm_model,
        ),
        fallback=FallbackNarrativeGenerator(),
    )


def get_current_user_id(request: Request) -> str | None:
    settings = get_settings()
    if settings.clerk_secret_key and settings.clerk_publishable_key:
        token = extract_clerk_token(request)
        if token is None:
            return None
        try:
            verified = verify_clerk_session_token(
                token=token,
                publishable_key=settings.clerk_publishable_key,
                secret_key=settings.clerk_secret_key,
                authorized_party=str(request.base_url).rstrip("/"),
            )
        except ClerkAuthenticationError:
            return None
        return verified.user_id
    return extract_stub_user_id(request)


def extract_clerk_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = value.strip()
            if token:
                return token
    cookie_value = request.cookies.get("__session")
    if cookie_value:
        return cookie_value.strip() or None
    return None


def extract_stub_user_id(request: Request) -> str | None:
    header_value = request.headers.get("x-md-preflight-user-id")
    if header_value:
        return header_value.strip() or None
    cookie_value = request.cookies.get("md_preflight_user_id")
    if cookie_value:
        return cookie_value.strip() or None
    return None
