from app.core.config import Settings, get_settings
from app.services.run_store import RUN_STORE, RunStore


def get_run_store() -> RunStore:
    return RUN_STORE


def get_app_settings() -> Settings:
    return get_settings()
