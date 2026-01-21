"""Base classes for stages."""

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
    """Context passed between stages in a pipeline."""

    url: str
    response_body: str | None = None
    response_headers: dict[str, str] = field(default_factory=lambda: {})
    status_code: int | None = None
    values: dict[str, Any] = field(default_factory=lambda: {})
    elapsed_ms: float = 0.0


class Stage(ABC):
    """Base class for all stages."""

    name: str = "base"
    description: str = "Base stage"

    # Whether this stage makes HTTP requests (vs transforms data)
    is_network_stage: bool = True

    @abstractmethod
    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Perform the check and return result.

        Args:
            url: URL to check
            verbose: Whether to include verbose output
            context: Optional context from previous stages

        Returns:
            CheckResult with status, message, and details
        """
        pass
