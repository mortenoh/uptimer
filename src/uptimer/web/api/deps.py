"""API dependencies for dependency injection."""

import base64
from functools import lru_cache

from fastapi import HTTPException, Request, status

from uptimer.settings import get_settings
from uptimer.storage import Storage


@lru_cache
def get_storage() -> Storage:
    """Get storage instance (cached)."""
    settings = get_settings()
    return Storage(
        mongodb_uri=settings.mongodb_uri,
        mongodb_db=settings.mongodb_db,
        results_retention=settings.results_retention,
    )


def clear_storage_cache() -> None:
    """Clear the storage cache (useful for testing)."""
    get_storage.cache_clear()


def _check_basic_auth(request: Request) -> str | None:
    """Check for valid Basic Auth header.

    Returns username if valid, None otherwise.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Basic "):
        return None

    try:
        encoded = auth_header[6:]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)

        settings = get_settings()
        if username == settings.username and password == settings.password:
            return username
    except (ValueError, UnicodeDecodeError):
        pass

    return None


def require_auth(request: Request) -> str:
    """Require authentication and return username.

    Supports both session-based auth and Basic Auth.

    Args:
        request: FastAPI request

    Returns:
        Username of authenticated user

    Raises:
        HTTPException: If not authenticated
    """
    # Check session first
    user: str | None = request.session.get("user")
    if user:
        return user

    # Check Basic Auth
    user = _check_basic_auth(request)
    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Basic"},
    )
