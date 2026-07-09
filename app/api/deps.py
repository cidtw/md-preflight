from __future__ import annotations

import logging

from anthropic import Anthropic
from fastapi import Request
from openai import OpenAI

from app.core.config import Settings, get_settings
from app.services.clerk_auth import ClerkAuthenticationError, verify_clerk_session_token
from app.services.history_store import HISTORY_STORE as DEFAULT_HISTORY_STORE
from app.services.history_store import HistoryStore, InMemoryHistoryStore, build_history_store
from app.services.llm_service import (
    FallbackNarrativeGenerator,
    FallbackOnErrorNarrativeGenerator,
    LLMNarrativeGenerator,
    NarrativeGenerator,
    OpenAINarrativeGenerator,
)
from app.services.run_store import RUN_STORE as DEFAULT_RUN_STORE
from app.services.run_store import InMemoryRunStore, RunStore, build_run_store

_history_store_initialized = False
history_store_instance: HistoryStore = DEFAULT_HISTORY_STORE
_run_store_initialized = False
run_store_instance: RunStore = DEFAULT_RUN_STORE
logger = logging.getLogger(__name__)


def get_run_store() -> RunStore:
    global run_store_instance, _run_store_initialized
    if not _run_store_initialized:
        if type(run_store_instance).__name__ == "InMemoryRunStore":
            try:
                run_store_instance = build_run_store()
            except Exception:
                logger.exception("run store initialization failed; degrading to in-memory store")
                run_store_instance = InMemoryRunStore()
        _run_store_initialized = True
    return run_store_instance


def get_history_store() -> HistoryStore:
    global history_store_instance, _history_store_initialized
    if not _history_store_initialized:
        if type(history_store_instance).__name__ == "InMemoryHistoryStore":
            try:
                history_store_instance = build_history_store()
            except Exception:
                logger.exception(
                    "history store initialization failed; degrading to in-memory store"
                )
                history_store_instance = InMemoryHistoryStore()
        _history_store_initialized = True
    return history_store_instance


def get_app_settings() -> Settings:
    return get_settings()


def get_narrative_generator(*, settings: Settings, use_llm: bool) -> NarrativeGenerator:
    if not use_llm:
        return FallbackNarrativeGenerator()

    if settings.openai_api_key:
        return FallbackOnErrorNarrativeGenerator(
            primary=OpenAINarrativeGenerator(
                client=OpenAI(api_key=settings.openai_api_key),
                model=settings.openai_model,
            ),
            fallback=FallbackNarrativeGenerator(),
        )

    if not settings.anthropic_api_key:
        return FallbackNarrativeGenerator()

    return FallbackOnErrorNarrativeGenerator(
        primary=LLMNarrativeGenerator(
            client=Anthropic(api_key=settings.anthropic_api_key),
            model=settings.llm_model,
        ),
        fallback=FallbackNarrativeGenerator(),
    )


def get_current_user_id(request: Request) -> str | None:
    settings = get_settings()
    mode = settings.auth_mode
    if mode == "clerk":
        # auth_mode derivation guarantees clerk_publishable_key is non-None here
        # (clerk_secret_key is also guaranteed set, but only gates auth_mode --
        # see clerk_auth.verify_clerk_session_token for why it isn't used below).
        assert settings.clerk_publishable_key is not None
        token = extract_clerk_token(request)
        if token is None:
            return None
        try:
            verified = verify_clerk_session_token(
                token=token,
                publishable_key=settings.clerk_publishable_key,
                authorized_parties=resolve_clerk_authorized_parties(settings),
            )
        except ClerkAuthenticationError:
            return None
        return verified.user_id
    if mode == "stub":
        return extract_stub_user_id(request)
    return None


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


def resolve_clerk_authorized_parties(settings: Settings) -> frozenset[str]:
    configured = settings.clerk_authorized_origins or tuple(settings.cors_origins)
    return frozenset(origin.rstrip("/") for origin in configured if origin.strip())
