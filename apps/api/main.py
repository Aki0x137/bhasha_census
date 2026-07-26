"""FastAPI application entrypoint."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from apps.api.db.session_store import init_db
from apps.api.routes.video import router as video_router
from apps.api.routes.sessions import router as sessions_router
from shared.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

_WEBAPP_DIR = Path(__file__).parent.parent.parent / "kyc_bot" / "webapp"

app = FastAPI(title="Bhasaha Census API", version="0.1.0")
app.include_router(video_router)
app.include_router(sessions_router)

if _WEBAPP_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_WEBAPP_DIR)), name="static")


@app.get("/liveness", include_in_schema=False)
def liveness_page() -> FileResponse:
    """Serve the browser-based liveness challenge page."""
    html = _WEBAPP_DIR / "liveness.html"
    if not html.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="liveness.html not found")
    return FileResponse(
        str(html),
        media_type="text/html",
        headers={
            # Allow getUserMedia when opened via tunnel / Mini App WebView
            "Permissions-Policy": "camera=(self), microphone=()",
            "Feature-Policy": "camera 'self'",
        },
    )


@app.on_event("startup")
async def startup() -> None:
    init_db()
    import services.video.plugins  # noqa: F401 — auto-registers all default plugins
    logger.info("api_startup", plugins_registered=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", path=str(request.url), error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
