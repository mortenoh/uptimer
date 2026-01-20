"""Tests for the CLI."""

from typer.testing import CliRunner

from uptimer.cli import app

runner = CliRunner()


def test_version() -> None:
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_check_success() -> None:
    """Test check command with valid URL."""
    result = runner.invoke(app, ["check", "https://httpbin.org/status/200"])
    assert result.exit_code == 0
    assert "UP" in result.output


def test_check_not_found() -> None:
    """Test check command with 404 response."""
    result = runner.invoke(app, ["check", "https://httpbin.org/status/404"])
    assert result.exit_code == 0
    assert "DEGRADED" in result.output


def test_check_without_protocol() -> None:
    """Test check command auto-adds https://."""
    result = runner.invoke(app, ["check", "httpbin.org/status/200"])
    assert result.exit_code == 0
    assert "UP" in result.output
