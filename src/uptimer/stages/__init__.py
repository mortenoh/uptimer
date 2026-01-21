"""Pluggable stage system for uptimer."""

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.dhis2 import Dhis2Stage
from uptimer.stages.http import HttpStage
from uptimer.stages.registry import get_stage, list_stages, register_stage

__all__ = [
    "Stage",
    "CheckContext",
    "CheckResult",
    "Status",
    "HttpStage",
    "Dhis2Stage",
    "register_stage",
    "get_stage",
    "list_stages",
]
