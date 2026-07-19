from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import Settings, get_settings

WEB_DIR = Path(__file__).parent / "web"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Store-specific ROP adjustment: store/trade parameters → internal "
            "score + knowledge match → LT/ROP recommendation report. "
            "v1 promotion preflight is archived."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.middleware("http")
    async def static_cache_headers(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            # Fingerprint-less assets: short public cache + revalidate window.
            response.headers["Cache-Control"] = (
                "public, max-age=3600, stale-while-revalidate=86400"
            )
        return response

    if WEB_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        def index() -> HTMLResponse:
            return HTMLResponse(build_index_html(settings))

        # Allow HEAD for uptime probes (was 405 with GET-only).
        app.add_api_route(
            "/",
            index,
            methods=["GET", "HEAD"],
            include_in_schema=False,
            response_class=HTMLResponse,
        )

    return app


def build_index_html(settings: Settings) -> str:
    html_path = WEB_DIR / "index.html"
    if not html_path.is_file():
        return (
            f"<html><body><h1>{settings.app_name}</h1>"
            f"<p>version {settings.app_version}</p></body></html>"
        )
    return html_path.read_text(encoding="utf-8").replace(
        "__APP_VERSION__",
        settings.app_version,
    )


app = create_app()
