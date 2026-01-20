"""API dependencies for dependency injection."""

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


def require_auth(request: Request) -> str:
    """Require authentication and return username.

    Args:
        request: FastAPI request

    Returns:
        Username of authenticated user

    Raises:
        HTTPException: If not authenticated
    """
    user: str | None = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
