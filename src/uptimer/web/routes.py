"""Web routes for uptimer."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from uptimer.settings import Settings, get_settings

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter()


def get_current_user(request: Request) -> str | None:
    """Get current user from session."""
    return request.session.get("user")


@router.get("/", response_model=None)
async def index(request: Request, user: str | None = Depends(get_current_user)) -> RedirectResponse:
    """Home page - redirect to login or dashboard."""
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None) -> HTMLResponse:
    """Login page."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error},
    )


@router.post("/login")
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Handle login form submission."""
    if username == settings.username and password == settings.password:
        request.session["user"] = username
        return RedirectResponse(url="/dashboard", status_code=302)

    return RedirectResponse(url="/login?error=Invalid+credentials", status_code=302)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Logout and clear session."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/dashboard", response_model=None)
async def dashboard(request: Request, user: str | None = Depends(get_current_user)) -> HTMLResponse | RedirectResponse:
    """Dashboard page."""
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user},
    )


