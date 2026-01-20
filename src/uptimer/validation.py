"""Validation helpers for monitors."""

from urllib.parse import urlparse

from uptimer.checkers.registry import list_checkers


def validate_url(url: str) -> str:
    """Validate and normalize URL.

    Args:
        url: URL to validate

    Returns:
        Normalized URL with scheme

    Raises:
        ValueError: If URL is invalid
    """
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty")

    # Add https:// if no scheme
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)

    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    return url


def validate_checker(checker: str) -> str:
    """Validate checker type exists in registry.

    Args:
        checker: Checker name to validate

    Returns:
        Validated checker name

    Raises:
        ValueError: If checker doesn't exist
    """
    available = list_checkers()
    if checker not in available:
        raise ValueError(f"Unknown checker: {checker}. Available: {', '.join(available)}")
    return checker


def validate_interval(interval: int) -> int:
    """Validate check interval.

    Args:
        interval: Interval in seconds

    Returns:
        Validated interval

    Raises:
        ValueError: If interval is less than 10 seconds
    """
    if interval < 10:
        raise ValueError(f"Interval must be at least 10 seconds, got {interval}")
    return interval
