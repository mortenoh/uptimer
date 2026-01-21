"""Tests for stages."""

import pytest

from uptimer.stages import CheckResult, Status, get_stage, list_stages
from uptimer.stages.http import HttpStage


def test_list_stages() -> None:
    """Test listing available stages."""
    stage_names = list_stages()
    assert "http" in stage_names
    assert "dhis2" in stage_names


def test_get_stage() -> None:
    """Test getting a stage by name."""
    stage_class = get_stage("http")
    assert stage_class == HttpStage


def test_get_unknown_stage() -> None:
    """Test getting unknown stage raises error."""
    with pytest.raises(ValueError, match="Unknown stage"):
        get_stage("unknown")


def test_http_stage_up() -> None:
    """Test HTTP stage with successful response."""
    stage = HttpStage()
    result = stage.check("https://httpbin.org/status/200")

    assert result.status == Status.UP
    assert result.url == "https://httpbin.org/status/200"
    assert result.message == "200"
    assert result.elapsed_ms > 0
    assert result.details["status_code"] == 200


def test_http_stage_degraded() -> None:
    """Test HTTP stage with 4xx/5xx response."""
    stage = HttpStage()
    result = stage.check("https://httpbin.org/status/500")

    assert result.status == Status.DEGRADED
    assert result.message == "500"


def test_http_stage_adds_https() -> None:
    """Test HTTP stage adds https:// prefix."""
    stage = HttpStage()
    result = stage.check("httpbin.org/status/200")

    assert result.url == "https://httpbin.org/status/200"
    assert result.status == Status.UP


def test_http_stage_follows_redirects() -> None:
    """Test HTTP stage follows redirects."""
    stage = HttpStage()
    result = stage.check("https://httpbin.org/redirect/1")

    assert result.status == Status.UP
    assert "redirects" in result.details


def test_http_stage_timeout() -> None:
    """Test HTTP stage with very short timeout."""
    stage = HttpStage(timeout=0.001)
    result = stage.check("https://httpbin.org/delay/1")

    assert result.status == Status.DOWN


def test_http_stage_custom_headers() -> None:
    """Test HTTP stage with custom headers."""
    stage = HttpStage(headers={"X-Custom-Header": "test-value"})
    result = stage.check("https://httpbin.org/headers")

    assert result.status == Status.UP
    # httpbin.org/headers returns the request headers in the response


def test_http_stage_authorization_header() -> None:
    """Test HTTP stage with Authorization header."""
    stage = HttpStage(headers={"Authorization": "Bearer test-token"})
    result = stage.check("https://httpbin.org/headers")

    assert result.status == Status.UP


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


# DHIS2 integration tests
class TestDhis2Stage:
    """Integration tests for DHIS2 stage."""

    @pytest.mark.integration
    def test_dhis2_stage_with_valid_credentials(self) -> None:
        """Test DHIS2 stage returns version info with valid credentials."""
        from uptimer.stages.dhis2 import Dhis2Stage

        stage = Dhis2Stage(username="admin", password="district", timeout=30.0)  # pyright: ignore[reportCallIssue]
        result = stage.check("https://play.dhis2.org/demo")

        assert result.status == Status.UP
        assert "version" in result.details
        assert "system_name" in result.details
        assert "revision" in result.details
        assert result.details["version"] is not None

    @pytest.mark.integration
    def test_dhis2_stage_with_invalid_credentials(self) -> None:
        """Test DHIS2 stage fails with invalid credentials."""
        from uptimer.stages.dhis2 import Dhis2Stage

        stage = Dhis2Stage(username="invalid", password="invalid", timeout=30.0)  # pyright: ignore[reportCallIssue]
        result = stage.check("https://play.dhis2.org/demo")

        assert result.status == Status.DOWN
        assert result.message == "Authentication failed"

    @pytest.mark.integration
    def test_dhis2_stage_captures_base_url(self) -> None:
        """Test DHIS2 stage resolves and captures the final base URL."""
        from uptimer.stages.dhis2 import Dhis2Stage

        stage = Dhis2Stage(username="admin", password="district", timeout=30.0)  # pyright: ignore[reportCallIssue]
        result = stage.check("https://play.dhis2.org/demo")

        assert result.status == Status.UP
        assert "base_url" in result.details
        assert "api_url" in result.details
        # URL should have been resolved through redirects
        assert "play.im.dhis2.org" in result.details["base_url"]
