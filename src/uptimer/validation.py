"""Validation helpers for monitors."""

from urllib.parse import urlparse

from uptimer.stages.registry import list_stages


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


def validate_stage(stage: str) -> str:
    """Validate stage type exists in registry.

    Args:
        stage: Stage name to validate

    Returns:
        Validated stage name

    Raises:
        ValueError: If stage doesn't exist
    """
    available = list_stages()
    if stage not in available:
        raise ValueError(f"Unknown stage: {stage}. Available: {', '.join(available)}")
    return stage


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
