"""Pluggable checker system for uptimer."""

from uptimer.checkers.base import CheckContext, Checker, CheckResult, Status
from uptimer.checkers.dhis2 import Dhis2Checker
from uptimer.checkers.http import HttpChecker
from uptimer.checkers.registry import get_checker, list_checkers, register_checker

__all__ = [
    "Checker",
    "CheckContext",
    "CheckResult",
    "Status",
    "HttpChecker",
    "Dhis2Checker",
    "register_checker",
    "get_checker",
    "list_checkers",
]
