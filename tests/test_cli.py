"""Tests for the CLI."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import respx
from typer.testing import CliRunner

from uptimer.cli import app
from uptimer.settings import clear_settings_cache

runner = CliRunner()

BASE_URL = "http://localhost:8000"


def setup_function() -> None:
    """Clear settings cache before each test."""
    clear_settings_cache()


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
    assert "list" in result.output
    assert "add" in result.output
    assert "check" in result.output
    assert "serve" in result.output
    assert "checkers" in result.output


def test_checkers_list() -> None:
    """Test checkers command lists available checkers."""
    result = runner.invoke(app, ["checkers"])
    assert result.exit_code == 0
    assert "http" in result.output
    assert "dhis2" in result.output


def test_checkers_list_json() -> None:
    """Test checkers command with JSON output."""
    result = runner.invoke(app, ["--json", "checkers"])
    assert result.exit_code == 0
    data: list[dict[str, str]] = json.loads(result.output)
    assert isinstance(data, list)
    names = [c["name"] for c in data]
    assert "http" in names


@respx.mock
def test_list_monitors() -> None:
    """Test list monitors command."""
    monitors = [
        {
            "id": "abc123",
            "name": "Test Monitor",
            "url": "https://example.com",
            "checks": [{"type": "http"}],
            "interval": 30,
            "schedule": None,
            "enabled": True,
            "tags": [],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "last_check": "2024-01-01T12:00:00Z",
            "last_status": "up",
        }
    ]
    respx.get(f"{BASE_URL}/api/monitors").mock(return_value=httpx.Response(200, json=monitors))

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Test Monitor" in result.output
    assert "example.com" in result.output


@respx.mock
def test_list_monitors_empty() -> None:
    """Test list monitors command with no monitors."""
    respx.get(f"{BASE_URL}/api/monitors").mock(return_value=httpx.Response(200, json=[]))

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No monitors found" in result.output


@respx.mock
def test_list_monitors_with_tag() -> None:
    """Test list monitors with tag filter."""
    respx.get(f"{BASE_URL}/api/monitors").mock(return_value=httpx.Response(200, json=[]))

    result = runner.invoke(app, ["list", "--tag", "production"])
    assert result.exit_code == 0
    # Verify the request had the tag parameter
    assert respx.calls[0].request.url.params.get("tag") == "production"  # type: ignore[union-attr]


@respx.mock
def test_list_monitors_json() -> None:
    """Test list monitors with JSON output."""
    monitors = [
        {
            "id": "abc123",
            "name": "Test Monitor",
            "url": "https://example.com",
            "checks": [{"type": "http"}],
            "interval": 30,
            "schedule": None,
            "enabled": True,
            "tags": [],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "last_check": None,
            "last_status": None,
        }
    ]
    respx.get(f"{BASE_URL}/api/monitors").mock(return_value=httpx.Response(200, json=monitors))

    result = runner.invoke(app, ["--json", "list"])
    assert result.exit_code == 0
    data: list[dict[str, object]] = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "Test Monitor"


@respx.mock
def test_get_monitor() -> None:
    """Test get monitor command."""
    monitor = {
        "id": "abc123",
        "name": "Test Monitor",
        "url": "https://example.com",
        "checks": [{"type": "http"}],
        "interval": 30,
        "schedule": None,
        "enabled": True,
        "tags": ["production"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_check": "2024-01-01T12:00:00Z",
        "last_status": "up",
    }
    respx.get(f"{BASE_URL}/api/monitors/abc123").mock(return_value=httpx.Response(200, json=monitor))

    result = runner.invoke(app, ["get", "abc123"])
    assert result.exit_code == 0
    assert "Test Monitor" in result.output
    assert "example.com" in result.output
    assert "production" in result.output


@respx.mock
def test_get_monitor_not_found() -> None:
    """Test get monitor command with non-existent ID."""
    respx.get(f"{BASE_URL}/api/monitors/notfound").mock(return_value=httpx.Response(404, json={"detail": "Not found"}))

    result = runner.invoke(app, ["get", "notfound"])
    assert result.exit_code == 1
    assert "Not found" in result.output


@respx.mock
def test_add_monitor() -> None:
    """Test add monitor command."""
    created_monitor = {
        "id": "new123",
        "name": "New Monitor",
        "url": "https://example.com",
        "checks": [{"type": "http"}],
        "interval": 30,
        "schedule": None,
        "enabled": True,
        "tags": [],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_check": None,
        "last_status": None,
    }
    respx.post(f"{BASE_URL}/api/monitors").mock(return_value=httpx.Response(201, json=created_monitor))

    result = runner.invoke(app, ["add", "New Monitor", "https://example.com"])
    assert result.exit_code == 0
    assert "Created monitor" in result.output
    assert "New Monitor" in result.output


@respx.mock
def test_add_monitor_with_options() -> None:
    """Test add monitor command with all options."""
    created_monitor = {
        "id": "new123",
        "name": "API Monitor",
        "url": "https://api.example.com",
        "checks": [{"type": "http"}, {"type": "ssl"}],
        "interval": 60,
        "schedule": "*/5 * * * *",
        "enabled": True,
        "tags": ["production", "api"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_check": None,
        "last_status": None,
    }
    respx.post(f"{BASE_URL}/api/monitors").mock(return_value=httpx.Response(201, json=created_monitor))

    result = runner.invoke(
        app,
        [
            "add",
            "API Monitor",
            "https://api.example.com",
            "--check",
            "http",
            "--check",
            "ssl",
            "--tag",
            "production",
            "--tag",
            "api",
            "--interval",
            "60",
            "--schedule",
            "*/5 * * * *",
        ],
    )
    assert result.exit_code == 0
    assert "Created monitor" in result.output


@respx.mock
def test_delete_monitor() -> None:
    """Test delete monitor command."""
    respx.delete(f"{BASE_URL}/api/monitors/abc123").mock(return_value=httpx.Response(204))

    result = runner.invoke(app, ["delete", "abc123", "--force"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


@respx.mock
def test_delete_monitor_not_found() -> None:
    """Test delete monitor command with non-existent ID."""
    respx.delete(f"{BASE_URL}/api/monitors/notfound").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )

    result = runner.invoke(app, ["delete", "notfound", "--force"])
    assert result.exit_code == 1
    assert "Not found" in result.output


@respx.mock
def test_run_check() -> None:
    """Test check command."""
    check_result: dict[str, str | float | dict[str, object]] = {
        "id": "result123",
        "monitor_id": "abc123",
        "status": "up",
        "message": "http: 200 OK",
        "elapsed_ms": 150.5,
        "details": {},
        "checked_at": "2024-01-01T12:00:00Z",
    }
    respx.post(f"{BASE_URL}/api/monitors/abc123/check").mock(return_value=httpx.Response(200, json=check_result))

    result = runner.invoke(app, ["check", "abc123"])
    assert result.exit_code == 0
    assert "UP" in result.output
    assert "200 OK" in result.output


@respx.mock
def test_run_check_json() -> None:
    """Test check command with JSON output."""
    check_result: dict[str, str | float | dict[str, object]] = {
        "id": "result123",
        "monitor_id": "abc123",
        "status": "up",
        "message": "http: 200 OK",
        "elapsed_ms": 150.5,
        "details": {},
        "checked_at": "2024-01-01T12:00:00Z",
    }
    respx.post(f"{BASE_URL}/api/monitors/abc123/check").mock(return_value=httpx.Response(200, json=check_result))

    result = runner.invoke(app, ["--json", "check", "abc123"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "up"


@respx.mock
def test_check_all() -> None:
    """Test check-all command."""
    results: list[dict[str, str | float | dict[str, object]]] = [
        {
            "id": "result1",
            "monitor_id": "abc123",
            "status": "up",
            "message": "http: 200 OK",
            "elapsed_ms": 100.0,
            "details": {},
            "checked_at": "2024-01-01T12:00:00Z",
        },
        {
            "id": "result2",
            "monitor_id": "def456",
            "status": "down",
            "message": "http: Connection error",
            "elapsed_ms": 0.0,
            "details": {},
            "checked_at": "2024-01-01T12:00:00Z",
        },
    ]
    respx.post(f"{BASE_URL}/api/monitors/check-all").mock(return_value=httpx.Response(200, json=results))

    result = runner.invoke(app, ["check-all"])
    assert result.exit_code == 0
    assert "UP" in result.output
    assert "DOWN" in result.output


@respx.mock
def test_get_results() -> None:
    """Test results command."""
    results: list[dict[str, str | float | dict[str, object]]] = [
        {
            "id": "result1",
            "monitor_id": "abc123",
            "status": "up",
            "message": "http: 200 OK",
            "elapsed_ms": 100.0,
            "details": {},
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    respx.get(f"{BASE_URL}/api/monitors/abc123/results").mock(return_value=httpx.Response(200, json=results))

    result = runner.invoke(app, ["results", "abc123"])
    assert result.exit_code == 0
    assert "200 OK" in result.output


@respx.mock
def test_list_tags() -> None:
    """Test tags command."""
    tags = ["production", "staging", "api"]
    respx.get(f"{BASE_URL}/api/monitors/tags").mock(return_value=httpx.Response(200, json=tags))

    result = runner.invoke(app, ["tags"])
    assert result.exit_code == 0
    assert "production" in result.output
    assert "staging" in result.output
    assert "api" in result.output


@respx.mock
def test_list_tags_empty() -> None:
    """Test tags command with no tags."""
    respx.get(f"{BASE_URL}/api/monitors/tags").mock(return_value=httpx.Response(200, json=[]))

    result = runner.invoke(app, ["tags"])
    assert result.exit_code == 0
    assert "No tags found" in result.output


@respx.mock
def test_auth_failure() -> None:
    """Test authentication failure handling."""
    respx.get(f"{BASE_URL}/api/monitors").mock(return_value=httpx.Response(401, json={"detail": "Unauthorized"}))

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1
    assert "Authentication failed" in result.output


@respx.mock
def test_connection_error() -> None:
    """Test connection error handling."""
    respx.get(f"{BASE_URL}/api/monitors").mock(side_effect=httpx.ConnectError("Connection refused"))

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1
    assert "Failed to connect" in result.output


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
