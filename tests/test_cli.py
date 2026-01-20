"""Tests for the CLI."""

import os
from pathlib import Path

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


def test_init_creates_config(tmp_path: Path) -> None:
    """Test init command creates config.yaml from example."""
    os.chdir(tmp_path)
    example = tmp_path / "config.example.yaml"
    example.write_text("username: admin\npassword: secret\n")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Created config.yaml" in result.output

    config = tmp_path / "config.yaml"
    assert config.exists()
    assert config.read_text() == "username: admin\npassword: secret\n"


def test_init_already_exists(tmp_path: Path) -> None:
    """Test init command when config.yaml already exists."""
    os.chdir(tmp_path)
    (tmp_path / "config.example.yaml").write_text("example content")
    (tmp_path / "config.yaml").write_text("existing content")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "already exists" in result.output

    # Should not overwrite existing config
    assert (tmp_path / "config.yaml").read_text() == "existing content"


def test_init_no_example(tmp_path: Path) -> None:
    """Test init command when config.example.yaml is missing."""
    os.chdir(tmp_path)

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "not found" in result.output
