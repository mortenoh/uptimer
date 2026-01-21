"""Threshold stage - asserts values are within bounds."""

from typing import Any

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


def _resolve_value(value_ref: str, context: CheckContext) -> Any:
    """Resolve a value reference from context.

    Args:
        value_ref: Value reference like "$elapsed_ms", "$count", or literal
        context: Check context

    Returns:
        Resolved value
    """
    if not value_ref.startswith("$"):
        # Try to parse as number
        try:
            if "." in value_ref:
                return float(value_ref)
            return int(value_ref)
        except ValueError:
            return value_ref

    key = value_ref[1:]  # Remove $

    # Built-in values
    if key == "elapsed_ms":
        return context.elapsed_ms
    elif key == "status_code":
        return context.status_code
    elif key == "response_length":
        return len(context.response_body) if context.response_body else 0

    # User-defined values from extractors
    return context.values.get(key)


@register_stage
class ThresholdStage(Stage):
    """Assert a value is within min/max bounds."""

    name = "threshold"
    description = "Assert value is within threshold bounds"
    is_network_stage = False

    def __init__(
        self,
        value_ref: str = "$elapsed_ms",
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        """Initialize threshold stage.

        Args:
            value_ref: Value reference (e.g., "$elapsed_ms", "$count")
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
        """
        self.value_ref = value_ref
        self.min_value = min_value
        self.max_value = max_value

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check if value is within threshold bounds."""
        if context is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No context available",
                details={"error": "Context missing"},
            )

        value = _resolve_value(self.value_ref, context)

        if value is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Value not found: {self.value_ref}",
                details={"value_ref": self.value_ref, "error": "Value not found"},
            )

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Non-numeric value: {value}",
                details={"value_ref": self.value_ref, "value": value, "error": "Not a number"},
            )

        details: dict[str, Any] = {
            "value_ref": self.value_ref,
            "value": numeric_value,
            "min": self.min_value,
            "max": self.max_value,
        }

        # Check bounds
        if self.min_value is not None and numeric_value < self.min_value:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"{numeric_value} < {self.min_value}",
                details=details,
            )

        if self.max_value is not None and numeric_value > self.max_value:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"{numeric_value} > {self.max_value}",
                details=details,
            )

        # Build success message
        if self.min_value is not None and self.max_value is not None:
            msg = f"{self.min_value} <= {numeric_value} <= {self.max_value}"
        elif self.min_value is not None:
            msg = f"{numeric_value} >= {self.min_value}"
        elif self.max_value is not None:
            msg = f"{numeric_value} <= {self.max_value}"
        else:
            msg = f"value={numeric_value}"

        return CheckResult(
            status=Status.UP,
            url=url,
            message=msg,
            details=details,
        )
