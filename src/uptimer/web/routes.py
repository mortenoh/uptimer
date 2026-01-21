"""Web routes for uptimer."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from uptimer.settings import Settings, get_settings

router = APIRouter()


def get_current_user(request: Request) -> str | None:
    """Get current user from session."""
    return request.session.get("user")


@router.get("/", response_model=None)
async def index() -> JSONResponse:
    """API root - return service info."""
    return JSONResponse(
        {
            "service": "uptimer",
            "version": "0.1.0",
            "docs": "/docs",
            "api": "/api/monitors",
        }
    )


@router.post("/login")
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Handle login form submission."""
    if username == settings.username and password == settings.password:
        request.session["user"] = username
        return JSONResponse({"status": "ok", "user": username})

    return JSONResponse({"status": "error", "message": "Invalid credentials"}, status_code=401)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Logout and clear session."""
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
