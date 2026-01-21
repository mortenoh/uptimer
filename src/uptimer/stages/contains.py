"""Contains stage - validates response contains/excludes text or pattern."""

import re

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


@register_stage
class ContainsStage(Stage):
    """Check if response body contains or excludes a pattern."""

    name = "contains"
    description = "Check if response contains/excludes text or pattern"
    is_network_stage = False

    def __init__(self, pattern: str = "", negate: bool = False) -> None:
        """Initialize contains stage.

        Args:
            pattern: Text or regex pattern to search for
            negate: If True, fail if pattern IS found (expect absence)
        """
        self.pattern = pattern
        self.negate = negate

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check if response body contains/excludes pattern."""
        if context is None or context.response_body is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No response body to check",
                details={"error": "Context or response body missing"},
            )

        if not self.pattern:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No pattern specified",
                details={"error": "Pattern is required"},
            )

        body = context.response_body
        found = False
        match_info: dict[str, object] = {"pattern": self.pattern, "negate": self.negate}

        # Try regex first, fall back to literal search
        try:
            match = re.search(self.pattern, body)
            if match:
                found = True
                match_info["match"] = match.group()
                match_info["position"] = match.start()
        except re.error:
            # Invalid regex, do literal search
            if self.pattern in body:
                found = True
                pos = body.find(self.pattern)
                match_info["match"] = self.pattern
                match_info["position"] = pos

        # Determine result based on negate flag
        if self.negate:
            # Expect pattern to NOT be found
            if found:
                return CheckResult(
                    status=Status.DOWN,
                    url=url,
                    message=f"Pattern found (should be absent): {self.pattern}",
                    details=match_info,
                )
            else:
                return CheckResult(
                    status=Status.UP,
                    url=url,
                    message=f"Pattern absent (as expected): {self.pattern}",
                    details=match_info,
                )
        else:
            # Expect pattern to be found
            if found:
                return CheckResult(
                    status=Status.UP,
                    url=url,
                    message=f"Pattern found: {self.pattern}",
                    details=match_info,
                )
            else:
                return CheckResult(
                    status=Status.DOWN,
                    url=url,
                    message=f"Pattern not found: {self.pattern}",
                    details=match_info,
                )
