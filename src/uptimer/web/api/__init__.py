"""API package for uptimer."""

from uptimer.web.api.monitors import router as monitors_router
from uptimer.web.api.stages import router as stages_router

__all__ = ["monitors_router", "stages_router"]
