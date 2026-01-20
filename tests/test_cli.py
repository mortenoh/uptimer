"""Tests for the CLI."""

from typer.testing import CliRunner

from uptimer.cli import app

runner = CliRunner()


def test_version() -> None:
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_version_flag() -> None:
    """Test --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help() -> None:
    """Test help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "check" in result.output
    assert "serve" in result.output
    assert "checkers" in result.output


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


def test_check_verbose() -> None:
    """Test check command with verbose output."""
    result = runner.invoke(app, ["check", "httpbin.org/status/200", "-v"])
    assert result.exit_code == 0
    assert "UP" in result.output
    assert "Time:" in result.output


def test_check_json_output() -> None:
    """Test check command with JSON output."""
    result = runner.invoke(app, ["--json", "check", "httpbin.org/status/200"])
    assert result.exit_code == 0
    assert '"status": "up"' in result.output


def test_checkers_list() -> None:
    """Test checkers command lists available checkers."""
    result = runner.invoke(app, ["checkers"])
    assert result.exit_code == 0
    assert "http" in result.output
    assert "dhis2" in result.output


def test_check_with_checker_option() -> None:
    """Test check with explicit checker option."""
    result = runner.invoke(app, ["check", "httpbin.org/status/200", "-c", "http"])
    assert result.exit_code == 0
    assert "UP" in result.output


def test_check_invalid_checker() -> None:
    """Test check with invalid checker."""
    result = runner.invoke(app, ["check", "example.com", "-c", "invalid"])
    assert result.exit_code == 1
    assert result.exception is not None
    assert "Unknown checker" in str(result.exception)
