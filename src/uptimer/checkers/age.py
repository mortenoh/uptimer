"""Age checker - validates timestamp freshness."""

from datetime import datetime, timezone
from typing import Any

from uptimer.checkers.base import CheckContext, Checker, CheckResult, Status
from uptimer.checkers.registry import register_checker


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse various timestamp formats into datetime.

    Args:
        value: Timestamp value (string, int, float, datetime)

    Returns:
        Parsed datetime or None
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        # Unix timestamp
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OSError, OverflowError):
            return None

    if isinstance(value, str):
        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    return None


@register_checker
class AgeChecker(Checker):
    """Check if a timestamp value is within acceptable age."""

    name = "age"
    description = "Validate timestamp freshness"
    is_network_checker = False

    def __init__(
        self,
        value_ref: str = "$server_time",
        max_age: int = 3600,
    ) -> None:
        """Initialize age checker.

        Args:
            value_ref: Reference to timestamp value (e.g., "$last_updated")
            max_age: Maximum allowed age in seconds
        """
        self.value_ref = value_ref
        self.max_age = max_age

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check if timestamp is within acceptable age."""
        if context is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No context available",
                details={"error": "Context missing"},
            )

        # Resolve value reference
        if self.value_ref.startswith("$"):
            key = self.value_ref[1:]
            value = context.values.get(key)
        else:
            value = self.value_ref

        if value is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Value not found: {self.value_ref}",
                details={"value_ref": self.value_ref, "error": "Value not found"},
            )

        timestamp = _parse_timestamp(value)
        if timestamp is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Could not parse timestamp: {value}",
                details={"value_ref": self.value_ref, "value": str(value), "error": "Invalid timestamp format"},
            )

        now = datetime.now(timezone.utc)
        age_seconds = (now - timestamp).total_seconds()

        details = {
            "value_ref": self.value_ref,
            "timestamp": timestamp.isoformat(),
            "age_seconds": age_seconds,
            "max_age": self.max_age,
        }

        if age_seconds < 0:
            return CheckResult(
                status=Status.DEGRADED,
                url=url,
                message=f"Timestamp is in the future by {abs(int(age_seconds))}s",
                details=details,
            )

        if age_seconds > self.max_age:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Too old: {int(age_seconds)}s > {self.max_age}s",
                details=details,
            )

        return CheckResult(
            status=Status.UP,
            url=url,
            message=f"Age: {int(age_seconds)}s (max: {self.max_age}s)",
            details=details,
        )
