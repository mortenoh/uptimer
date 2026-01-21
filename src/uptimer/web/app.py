"""FastAPI application for uptimer web UI."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from uptimer.scheduler import start_scheduler, stop_scheduler
from uptimer.settings import get_settings
from uptimer.web.api import monitors_router, stages_router
from uptimer.web.api.deps import get_storage
from uptimer.web.routes import router

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan - start/stop scheduler."""
    # Startup
    storage = get_storage()
    start_scheduler(storage)
    yield
    # Shutdown
    stop_scheduler()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Uptimer",
        description="Service uptime monitoring",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware for frontend access
    cors_origins = (
        ["*"] if settings.cors_origins == "*" else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session middleware for cookie-based auth
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="uptimer_session",
        max_age=settings.session_max_age,
    )

    # Mount static files if directory exists
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # Include routes
    app.include_router(router)
    app.include_router(monitors_router)
    app.include_router(stages_router)

    return app
