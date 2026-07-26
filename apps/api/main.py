"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from apps.api.db.session_store import init_db
from apps.api.routes.video import router as video_router
from apps.api.routes.sessions import router as sessions_router
from shared.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title="Bhasaha Census API", version="0.1.0")
app.include_router(video_router)
app.include_router(sessions_router)


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
