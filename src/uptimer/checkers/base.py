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


class Checker(ABC):
    """Base class for all checkers."""

    name: str = "base"
    description: str = "Base checker"

    @abstractmethod
    def check(self, url: str, verbose: bool = False) -> CheckResult:
        """Perform the check and return result."""
        pass
