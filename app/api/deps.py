import os

from anthropic import Anthropic

from app.core.config import Settings, get_settings
from app.services.llm_service import (
    FallbackNarrativeGenerator,
    FallbackOnErrorNarrativeGenerator,
    LLMNarrativeGenerator,
    NarrativeGenerator,
)
from app.services.run_store import RUN_STORE, RunStore


def get_run_store() -> RunStore:
    return RUN_STORE


def get_app_settings() -> Settings:
    return get_settings()


def get_narrative_generator(*, settings: Settings, use_llm: bool) -> NarrativeGenerator:
    if not use_llm:
        return FallbackNarrativeGenerator()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return FallbackNarrativeGenerator()

    return FallbackOnErrorNarrativeGenerator(
        primary=LLMNarrativeGenerator(
            client=Anthropic(api_key=api_key),
            model=settings.llm_model,
        ),
        fallback=FallbackNarrativeGenerator(),
    )
