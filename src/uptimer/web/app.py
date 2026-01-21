"""FastAPI application for uptimer web UI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from uptimer.settings import get_settings
from uptimer.web.api import monitors_router
from uptimer.web.routes import router

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Uptimer",
        description="Service uptime monitoring",
        version="0.1.0",
    )

    # CORS middleware for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session middleware for cookie-based auth
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="uptimer_session",
        max_age=86400,  # 24 hours
    )

    # Mount static files if directory exists
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # Include routes
    app.include_router(router)
    app.include_router(monitors_router)

    return app
