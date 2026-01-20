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

    # Import all checker modules to trigger @register_checker decorators
    from uptimer.checkers import age as _age  # noqa: F401
    from uptimer.checkers import contains as _contains  # noqa: F401
    from uptimer.checkers import dhis2 as _dhis2  # noqa: F401
    from uptimer.checkers import dhis2_checks as _dhis2_checks  # noqa: F401
    from uptimer.checkers import dns as _dns  # noqa: F401
    from uptimer.checkers import header as _header  # noqa: F401
    from uptimer.checkers import jq as _jq  # noqa: F401
    from uptimer.checkers import json_schema as _json_schema  # noqa: F401
    from uptimer.checkers import jsonpath as _jsonpath  # noqa: F401
    from uptimer.checkers import regex as _regex  # noqa: F401
    from uptimer.checkers import ssl as _ssl  # noqa: F401
    from uptimer.checkers import tcp as _tcp  # noqa: F401
    from uptimer.checkers import threshold as _threshold  # noqa: F401

    # Mark as used to satisfy pyright
    _ = (
        _age,
        _contains,
        _dhis2,
        _dhis2_checks,
        _dns,
        _header,
        _jq,
        _json_schema,
        _jsonpath,
        _regex,
        _ssl,
        _tcp,
        _threshold,
    )


_register_defaults()
