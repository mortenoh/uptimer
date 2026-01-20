"""Base classes for checkers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(Enum):
    """Check result status."""

    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class CheckResult:
    """Result of a check."""

    status: Status
    url: str
    message: str
    elapsed_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=lambda: {})


@dataclass
class CheckContext:
    """Context passed between checks in a chain."""

    url: str
    response_body: str | None = None
    response_headers: dict[str, str] = field(default_factory=lambda: {})
    status_code: int | None = None
    values: dict[str, Any] = field(default_factory=lambda: {})
    elapsed_ms: float = 0.0


class Checker(ABC):
    """Base class for all checkers."""

    name: str = "base"
    description: str = "Base checker"

    # Whether this checker makes HTTP requests (vs transforms data)
    is_network_checker: bool = True

    @abstractmethod
    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Perform the check and return result.

        Args:
            url: URL to check
            verbose: Whether to include verbose output
            context: Optional context from previous checks

        Returns:
            CheckResult with status, message, and details
        """
        pass
