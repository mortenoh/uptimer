"""Tests for Pydantic schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from uptimer.schemas import CheckResultRecord, Monitor, MonitorCreate, MonitorUpdate, Stage


class TestStage:
    """Tests for Stage schema."""

    def test_http_stage(self) -> None:
        """Test creating HTTP stage config."""
        stage = Stage(type="http")
        assert stage.type == "http"
        assert stage.username is None
        assert stage.password is None

    def test_dhis2_stage_with_credentials(self) -> None:
        """Test creating DHIS2 stage config with credentials."""
        stage = Stage(type="dhis2", username="admin", password="district")
        assert stage.type == "dhis2"
        assert stage.username == "admin"
        assert stage.password == "district"

    def test_http_stage_with_headers(self) -> None:
        """Test creating HTTP stage config with custom headers."""
        stage = Stage(
            type="http",
            headers={"Authorization": "Bearer token", "X-Custom": "value"},
        )
        assert stage.type == "http"
        assert stage.headers == {"Authorization": "Bearer token", "X-Custom": "value"}

    def test_http_stage_headers_default_none(self) -> None:
        """Test that headers default to None."""
        stage = Stage(type="http")
        assert stage.headers is None


class TestMonitorCreate:
    """Tests for MonitorCreate schema."""

    def test_minimal_create(self) -> None:
        """Test creating monitor with minimal fields."""
        data = MonitorCreate(name="Test", url="https://example.com")
        assert data.name == "Test"
        assert data.url == "https://example.com"
        assert len(data.pipeline) == 1
        assert data.pipeline[0].type == "http"
        assert data.interval == 30
        assert data.enabled is True

    def test_full_create(self) -> None:
        """Test creating monitor with all fields."""
        data = MonitorCreate(
            name="Test Monitor",
            url="https://api.example.com",
            pipeline=[Stage(type="dhis2", username="admin", password="secret")],
            interval=120,
            enabled=False,
        )
        assert data.name == "Test Monitor"
        assert data.pipeline[0].type == "dhis2"
        assert data.pipeline[0].username == "admin"
        assert data.interval == 120
        assert data.enabled is False

    def test_multiple_stages(self) -> None:
        """Test creating monitor with multiple pipeline stages."""
        data = MonitorCreate(
            name="Multi",
            url="https://example.com",
            pipeline=[
                Stage(type="http"),
                Stage(type="dhis2", username="admin", password="pass"),
            ],
        )
        assert len(data.pipeline) == 2
        assert data.pipeline[0].type == "http"
        assert data.pipeline[1].type == "dhis2"

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

    def test_valid_cron_schedule(self) -> None:
        """Test valid cron expression is accepted."""
        data = MonitorCreate(name="Test", url="https://example.com", schedule="*/5 * * * *")
        assert data.schedule == "*/5 * * * *"

    def test_cron_schedule_every_hour(self) -> None:
        """Test hourly cron expression."""
        data = MonitorCreate(name="Test", url="https://example.com", schedule="0 * * * *")
        assert data.schedule == "0 * * * *"

    def test_cron_schedule_daily(self) -> None:
        """Test daily cron expression."""
        data = MonitorCreate(name="Test", url="https://example.com", schedule="0 9 * * *")
        assert data.schedule == "0 9 * * *"

    def test_cron_schedule_weekdays(self) -> None:
        """Test weekday cron expression."""
        data = MonitorCreate(name="Test", url="https://example.com", schedule="0 9 * * 1-5")
        assert data.schedule == "0 9 * * 1-5"

    def test_invalid_cron_schedule(self) -> None:
        """Test invalid cron expression is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MonitorCreate(name="Test", url="https://example.com", schedule="invalid")
        assert "Invalid cron expression" in str(exc_info.value)

    def test_invalid_cron_too_few_fields(self) -> None:
        """Test cron with too few fields is rejected."""
        with pytest.raises(ValidationError):
            MonitorCreate(name="Test", url="https://example.com", schedule="* * *")

    def test_schedule_none_allowed(self) -> None:
        """Test schedule can be None."""
        data = MonitorCreate(name="Test", url="https://example.com", schedule=None)
        assert data.schedule is None


class TestMonitorUpdate:
    """Tests for MonitorUpdate schema."""

    def test_empty_update(self) -> None:
        """Test empty update is valid."""
        data = MonitorUpdate()
        assert data.name is None
        assert data.url is None
        assert data.pipeline is None

    def test_partial_update(self) -> None:
        """Test partial update."""
        data = MonitorUpdate(name="New Name", interval=300)
        assert data.name == "New Name"
        assert data.interval == 300
        assert data.url is None
        assert data.enabled is None

    def test_update_pipeline(self) -> None:
        """Test updating pipeline."""
        data = MonitorUpdate(pipeline=[Stage(type="dhis2", username="u", password="p")])
        assert data.pipeline is not None
        assert len(data.pipeline) == 1
        assert data.pipeline[0].type == "dhis2"

    def test_name_validation_empty(self) -> None:
        """Test empty name in update is rejected."""
        with pytest.raises(ValidationError):
            MonitorUpdate(name="")

    def test_interval_validation_min(self) -> None:
        """Test interval below 10 in update is rejected."""
        with pytest.raises(ValidationError):
            MonitorUpdate(interval=5)

    def test_update_schedule(self) -> None:
        """Test updating schedule with valid cron."""
        data = MonitorUpdate(schedule="0 */2 * * *")
        assert data.schedule == "0 */2 * * *"

    def test_update_invalid_schedule(self) -> None:
        """Test updating schedule with invalid cron is rejected."""
        with pytest.raises(ValidationError):
            MonitorUpdate(schedule="not-a-cron")


class TestMonitor:
    """Tests for Monitor schema."""

    def test_full_monitor(self) -> None:
        """Test full monitor creation."""
        now = datetime.now(timezone.utc)
        monitor = Monitor(
            id="test-id",
            name="Test",
            url="https://example.com",
            pipeline=[Stage(type="http")],
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
        assert monitor.pipeline[0].type == "http"


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
