"""Checker registry for pluggable check system."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uptimer.checkers.base import Checker

_registry: dict[str, type["Checker"]] = {}


def register_checker(checker_class: type["Checker"]) -> type["Checker"]:
    """Register a checker class. Can be used as decorator."""
    _registry[checker_class.name] = checker_class
    return checker_class


def get_checker(name: str) -> type["Checker"]:
    """Get a checker class by name."""
    if name not in _registry:
        available = ", ".join(_registry.keys())
        raise ValueError(f"Unknown checker: {name}. Available: {available}")
    return _registry[name]


def list_checkers() -> list[str]:
    """List all registered checker names."""
    return list(_registry.keys())


def _register_defaults() -> None:
    """Register default checkers."""
    from uptimer.checkers.http import HttpChecker

    register_checker(HttpChecker)


_register_defaults()
