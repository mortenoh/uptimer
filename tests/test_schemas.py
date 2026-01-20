"""Tests for Pydantic schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from uptimer.schemas import CheckConfig, CheckResultRecord, Monitor, MonitorCreate, MonitorUpdate


class TestCheckConfig:
    """Tests for CheckConfig schema."""

    def test_http_check(self) -> None:
        """Test creating HTTP check config."""
        check = CheckConfig(type="http")
        assert check.type == "http"
        assert check.username is None
        assert check.password is None

    def test_dhis2_check_with_credentials(self) -> None:
        """Test creating DHIS2 check config with credentials."""
        check = CheckConfig(type="dhis2", username="admin", password="district")
        assert check.type == "dhis2"
        assert check.username == "admin"
        assert check.password == "district"


class TestMonitorCreate:
    """Tests for MonitorCreate schema."""

    def test_minimal_create(self) -> None:
        """Test creating monitor with minimal fields."""
        data = MonitorCreate(name="Test", url="https://example.com")
        assert data.name == "Test"
        assert data.url == "https://example.com"
        assert len(data.checks) == 1
        assert data.checks[0].type == "http"
        assert data.interval == 30
        assert data.enabled is True

    def test_full_create(self) -> None:
        """Test creating monitor with all fields."""
        data = MonitorCreate(
            name="Test Monitor",
            url="https://api.example.com",
            checks=[CheckConfig(type="dhis2", username="admin", password="secret")],
            interval=120,
            enabled=False,
        )
        assert data.name == "Test Monitor"
        assert data.checks[0].type == "dhis2"
        assert data.checks[0].username == "admin"
        assert data.interval == 120
        assert data.enabled is False

    def test_multiple_checks(self) -> None:
        """Test creating monitor with multiple checks."""
        data = MonitorCreate(
            name="Multi",
            url="https://example.com",
            checks=[
                CheckConfig(type="http"),
                CheckConfig(type="dhis2", username="admin", password="pass"),
            ],
        )
        assert len(data.checks) == 2
        assert data.checks[0].type == "http"
        assert data.checks[1].type == "dhis2"

    def test_name_validation_empty(self) -> None:
        """Test empty name is rejected."""
        with pytest.raises(ValidationError):
            MonitorCreate(name="", url="https://example.com")

    def test_name_validation_whitespace(self) -> None:
        """Test whitespace-only name is rejected."""
        with pytest.raises(ValidationError):
            MonitorCreate(name="   ", url="https://example.com")

    def test_name_validation_max_length(self) -> None:
        """Test name over 100 chars is rejected."""
        with pytest.raises(ValidationError):
            MonitorCreate(name="x" * 101, url="https://example.com")

    def test_name_trimmed(self) -> None:
        """Test name is trimmed."""
        data = MonitorCreate(name="  Test  ", url="https://example.com")
        assert data.name == "Test"

    def test_interval_validation_min(self) -> None:
        """Test interval below 10 is rejected."""
        with pytest.raises(ValidationError):
            MonitorCreate(name="Test", url="https://example.com", interval=5)


class TestMonitorUpdate:
    """Tests for MonitorUpdate schema."""

    def test_empty_update(self) -> None:
        """Test empty update is valid."""
        data = MonitorUpdate()
        assert data.name is None
        assert data.url is None
        assert data.checks is None

    def test_partial_update(self) -> None:
        """Test partial update."""
        data = MonitorUpdate(name="New Name", interval=300)
        assert data.name == "New Name"
        assert data.interval == 300
        assert data.url is None
        assert data.enabled is None

    def test_update_checks(self) -> None:
        """Test updating checks."""
        data = MonitorUpdate(checks=[CheckConfig(type="dhis2", username="u", password="p")])
        assert data.checks is not None
        assert len(data.checks) == 1
        assert data.checks[0].type == "dhis2"

    def test_name_validation_empty(self) -> None:
        """Test empty name in update is rejected."""
        with pytest.raises(ValidationError):
            MonitorUpdate(name="")

    def test_interval_validation_min(self) -> None:
        """Test interval below 10 in update is rejected."""
        with pytest.raises(ValidationError):
            MonitorUpdate(interval=5)


class TestMonitor:
    """Tests for Monitor schema."""

    def test_full_monitor(self) -> None:
        """Test full monitor creation."""
        now = datetime.now(timezone.utc)
        monitor = Monitor(
            id="test-id",
            name="Test",
            url="https://example.com",
            checks=[CheckConfig(type="http")],
            interval=60,
            enabled=True,
            created_at=now,
            updated_at=now,
            last_check=None,
            last_status=None,
        )
        assert monitor.id == "test-id"
        assert monitor.name == "Test"
        assert monitor.created_at == now
        assert monitor.checks[0].type == "http"


class TestCheckResultRecord:
    """Tests for CheckResultRecord schema."""

    def test_create_result(self) -> None:
        """Test creating a check result record."""
        now = datetime.now(timezone.utc)
        result = CheckResultRecord(
            id="result-id",
            monitor_id="monitor-id",
            status="up",
            message="200 OK",
            elapsed_ms=150.5,
            details={"status_code": 200},
            checked_at=now,
        )
        assert result.id == "result-id"
        assert result.monitor_id == "monitor-id"
        assert result.status == "up"
        assert result.elapsed_ms == 150.5
        assert result.details == {"status_code": 200}

    def test_default_details(self) -> None:
        """Test default empty details."""
        now = datetime.now(timezone.utc)
        result = CheckResultRecord(
            id="result-id",
            monitor_id="monitor-id",
            status="up",
            message="OK",
            elapsed_ms=100.0,
            checked_at=now,
        )
        assert result.details == {}
