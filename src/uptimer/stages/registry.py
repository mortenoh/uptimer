"""Stage registry for pluggable stage system."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uptimer.stages.base import Stage

_registry: dict[str, type["Stage"]] = {}


def register_stage(stage_class: type["Stage"]) -> type["Stage"]:
    """Register a stage class. Can be used as decorator."""
    _registry[stage_class.name] = stage_class
    return stage_class


def get_stage(name: str) -> type["Stage"]:
    """Get a stage class by name."""
    if name not in _registry:
        available = ", ".join(_registry.keys())
        raise ValueError(f"Unknown stage: {name}. Available: {available}")
    return _registry[name]


def list_stages() -> list[str]:
    """List all registered stage names."""
    return list(_registry.keys())


def _register_defaults() -> None:
    """Register default stages."""
    from uptimer.stages.http import HttpStage

    register_stage(HttpStage)

    # Import all stage modules to trigger @register_stage decorators
    from uptimer.stages import age as _age  # noqa: F401
    from uptimer.stages import contains as _contains  # noqa: F401
    from uptimer.stages import dhis2 as _dhis2  # noqa: F401
    from uptimer.stages import dhis2_checks as _dhis2_checks  # noqa: F401
    from uptimer.stages import dns as _dns  # noqa: F401
    from uptimer.stages import header as _header  # noqa: F401
    from uptimer.stages import jq as _jq  # noqa: F401
    from uptimer.stages import json_schema as _json_schema  # noqa: F401
    from uptimer.stages import jsonpath as _jsonpath  # noqa: F401
    from uptimer.stages import regex as _regex  # noqa: F401
    from uptimer.stages import ssl as _ssl  # noqa: F401
    from uptimer.stages import tcp as _tcp  # noqa: F401
    from uptimer.stages import threshold as _threshold  # noqa: F401

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
