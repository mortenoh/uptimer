"""Tests for checkers."""

import pytest

from uptimer.checkers import CheckResult, Status, get_checker, list_checkers
from uptimer.checkers.http import HttpChecker


def test_list_checkers() -> None:
    """Test listing available checkers."""
    checkers = list_checkers()
    assert "http" in checkers
    assert "dhis2" in checkers


def test_get_checker() -> None:
    """Test getting a checker by name."""
    checker_class = get_checker("http")
    assert checker_class == HttpChecker


def test_get_unknown_checker() -> None:
    """Test getting unknown checker raises error."""
    with pytest.raises(ValueError, match="Unknown checker"):
        get_checker("unknown")


def test_http_checker_up() -> None:
    """Test HTTP checker with successful response."""
    checker = HttpChecker()
    result = checker.check("https://httpbin.org/status/200")

    assert result.status == Status.UP
    assert result.url == "https://httpbin.org/status/200"
    assert result.message == "200"
    assert result.elapsed_ms > 0
    assert result.details["status_code"] == 200


def test_http_checker_degraded() -> None:
    """Test HTTP checker with 4xx/5xx response."""
    checker = HttpChecker()
    result = checker.check("https://httpbin.org/status/500")

    assert result.status == Status.DEGRADED
    assert result.message == "500"


def test_http_checker_adds_https() -> None:
    """Test HTTP checker adds https:// prefix."""
    checker = HttpChecker()
    result = checker.check("httpbin.org/status/200")

    assert result.url == "https://httpbin.org/status/200"
    assert result.status == Status.UP


def test_http_checker_follows_redirects() -> None:
    """Test HTTP checker follows redirects."""
    checker = HttpChecker()
    result = checker.check("https://httpbin.org/redirect/1")

    assert result.status == Status.UP
    assert "redirects" in result.details


def test_http_checker_timeout() -> None:
    """Test HTTP checker with very short timeout."""
    checker = HttpChecker(timeout=0.001)
    result = checker.check("https://httpbin.org/delay/1")

    assert result.status == Status.DOWN


def test_check_result_creation() -> None:
    """Test CheckResult dataclass."""
    result = CheckResult(
        status=Status.UP,
        url="https://example.com",
        message="OK",
        elapsed_ms=100.5,
        details={"key": "value"},
    )

    assert result.status == Status.UP
    assert result.url == "https://example.com"
    assert result.message == "OK"
    assert result.elapsed_ms == 100.5
    assert result.details == {"key": "value"}


def test_status_enum_values() -> None:
    """Test Status enum values."""
    assert Status.UP.value == "up"
    assert Status.DEGRADED.value == "degraded"
    assert Status.DOWN.value == "down"
