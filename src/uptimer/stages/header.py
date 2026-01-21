"""Header stage - extracts and validates HTTP response headers."""

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


@register_stage
class HeaderStage(Stage):
    """Extract or validate HTTP response headers."""

    name = "header"
    description = "Extract or validate response headers"
    is_network_stage = False

    def __init__(
        self,
        pattern: str = "",
        store_as: str | None = None,
        expected: str | None = None,
    ) -> None:
        """Initialize header stage.

        Args:
            pattern: Header name to extract (case-insensitive)
            store_as: Key to store header value in context
            expected: Expected header value (if validating)
        """
        self.header_name = pattern
        self.store_as = store_as
        self.expected = expected

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Extract or validate a response header."""
        if context is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No context available",
                details={"error": "Context missing"},
            )

        if not self.header_name:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No header name specified",
                details={"error": "Header name is required"},
            )

        # Case-insensitive header lookup
        headers_lower = {k.lower(): v for k, v in context.response_headers.items()}
        header_value = headers_lower.get(self.header_name.lower())

        if header_value is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Header not found: {self.header_name}",
                details={"header": self.header_name, "available_headers": list(context.response_headers.keys())},
            )

        # Store in context if store_as specified
        if self.store_as:
            context.values[self.store_as] = header_value

        # Validate if expected value provided
        if self.expected is not None:
            if header_value == self.expected:
                return CheckResult(
                    status=Status.UP,
                    url=url,
                    message=f"{self.header_name}={header_value}",
                    details={"header": self.header_name, "value": header_value, "expected": self.expected},
                )
            else:
                return CheckResult(
                    status=Status.DOWN,
                    url=url,
                    message=f"Expected {self.expected}, got {header_value}",
                    details={"header": self.header_name, "value": header_value, "expected": self.expected},
                )

        return CheckResult(
            status=Status.UP,
            url=url,
            message=f"{self.header_name}={header_value}",
            details={"header": self.header_name, "value": header_value},
        )
