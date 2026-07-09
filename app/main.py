import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import Settings, get_settings

WEB_DIR = Path(__file__).parent / "web"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="MD Preflight API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    # MVP web UI — static SPA served by FastAPI (same origin, no build step).
    if WEB_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        def index() -> HTMLResponse:
            return HTMLResponse(build_index_html(settings))

        app.add_api_route("/", index, include_in_schema=False, response_class=HTMLResponse)

    return app


def build_index_html(settings: Settings) -> str:
    config_payload = json.dumps(
        {
            "clerkPublishableKey": settings.clerk_publishable_key,
            "maxUploadBytes": settings.max_upload_bytes,
            "allowedExtensions": list(settings.allowed_extensions),
            "authMode": settings.auth_mode,
        },
        ensure_ascii=True,
    )
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    return html.replace(
        "<!-- __MDP_CONFIG_PLACEHOLDER__ -->",
        f"<script>window.__MDP_CONFIG__ = {config_payload};</script>",
    )


app = create_app()
