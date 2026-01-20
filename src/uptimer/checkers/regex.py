"""Regex checker - extracts values using regex capture groups."""

import re

from uptimer.checkers.base import CheckContext, Checker, CheckResult, Status
from uptimer.checkers.registry import register_checker


@register_checker
class RegexChecker(Checker):
    """Extract values from response using regex capture groups."""

    name = "regex"
    description = "Extract values using regex capture groups"
    is_network_checker = False

    def __init__(self, pattern: str = "", store_as: str | None = None) -> None:
        """Initialize regex checker.

        Args:
            pattern: Regex pattern with capture groups
            store_as: Key to store first capture group value in context
        """
        self.pattern = pattern
        self.store_as = store_as

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Extract values from response using regex."""
        if context is None or context.response_body is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No response body to extract from",
                details={"error": "Context or response body missing"},
            )

        if not self.pattern:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No pattern specified",
                details={"error": "Pattern is required"},
            )

        try:
            compiled = re.compile(self.pattern)
        except re.error as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Invalid regex: {e}",
                details={"pattern": self.pattern, "error": str(e)},
            )

        match = compiled.search(context.response_body)

        if not match:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="Pattern not matched",
                details={"pattern": self.pattern},
            )

        # Extract groups
        groups = match.groups()
        group_dict = match.groupdict()

        # Store first group in context if store_as specified
        if self.store_as and context is not None:
            if groups:
                context.values[self.store_as] = groups[0]
            elif group_dict:
                context.values[self.store_as] = next(iter(group_dict.values()))

        return CheckResult(
            status=Status.UP,
            url=url,
            message=f"extracted: {groups[0] if groups else match.group()}",
            details={
                "pattern": self.pattern,
                "match": match.group(),
                "groups": groups,
                "named_groups": group_dict,
            },
        )
