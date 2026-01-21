"""Tests for storage layer."""

import uuid
from datetime import datetime, timezone
from typing import Any

import mongomock
import pytest
from pymongo import MongoClient

from uptimer.schemas import CheckResultRecord, MonitorCreate, MonitorUpdate, Stage
from uptimer.storage import Storage


@pytest.fixture
def storage() -> Storage:
    """Create a storage instance with mongomock."""
    client: MongoClient[dict[str, Any]] = mongomock.MongoClient()
    return Storage(
        mongodb_uri="mongodb://localhost:27017",
        mongodb_db="test_uptimer",
        results_retention=10,
        client=client,
    )


class TestMonitorCRUD:
    """Tests for monitor CRUD operations."""

    def test_list_monitors_empty(self, storage: Storage) -> None:
        """Test listing monitors when empty."""
        monitors = storage.list_monitors()
        assert monitors == []

    def test_create_monitor(self, storage: Storage) -> None:
        """Test creating a monitor."""
        data = MonitorCreate(name="Test", url="https://example.com")
        monitor = storage.create_monitor(data)

        assert monitor.name == "Test"
        assert monitor.url == "https://example.com"
        assert monitor.id is not None
        assert monitor.created_at is not None
        assert monitor.updated_at is not None

    def test_create_monitor_normalizes_url(self, storage: Storage) -> None:
        """Test URL is normalized when creating monitor."""
        data = MonitorCreate(name="Test", url="example.com")
        monitor = storage.create_monitor(data)
        assert monitor.url == "https://example.com"

    def test_create_monitor_invalid_stage(self, storage: Storage) -> None:
        """Test creating monitor with invalid stage."""
        data = MonitorCreate(
            name="Test",
            url="https://example.com",
            pipeline=[Stage(type="invalid")],
        )
        with pytest.raises(ValueError, match="Unknown stage"):
            storage.create_monitor(data)

    def test_create_monitor_invalid_interval(self, storage: Storage) -> None:
        """Test creating monitor with invalid interval via validation."""
        # Note: Pydantic already validates >= 10 in the model
        data = MonitorCreate(name="Test", url="https://example.com", interval=60)
        monitor = storage.create_monitor(data)
        assert monitor.interval == 60

    def test_list_monitors_after_create(self, storage: Storage) -> None:
        """Test listing monitors after creating one."""
        data = MonitorCreate(name="Test", url="https://example.com")
        storage.create_monitor(data)

        monitors = storage.list_monitors()
        assert len(monitors) == 1
        assert monitors[0].name == "Test"

    def test_get_monitor(self, storage: Storage) -> None:
        """Test getting a monitor by ID."""
        data = MonitorCreate(name="Test", url="https://example.com")
        created = storage.create_monitor(data)

        monitor = storage.get_monitor(created.id)
        assert monitor is not None
        assert monitor.id == created.id
        assert monitor.name == "Test"

    def test_get_monitor_not_found(self, storage: Storage) -> None:
        """Test getting non-existent monitor."""
        monitor = storage.get_monitor("nonexistent")
        assert monitor is None

    def test_update_monitor(self, storage: Storage) -> None:
        """Test updating a monitor."""
        data = MonitorCreate(name="Test", url="https://example.com")
        created = storage.create_monitor(data)

        update = MonitorUpdate(name="Updated", interval=120)
        updated = storage.update_monitor(created.id, update)

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.interval == 120
        assert updated.url == "https://example.com"  # Unchanged

    def test_update_monitor_url_normalized(self, storage: Storage) -> None:
        """Test URL is normalized during update."""
        data = MonitorCreate(name="Test", url="https://example.com")
        created = storage.create_monitor(data)

        update = MonitorUpdate(url="new.example.com")
        updated = storage.update_monitor(created.id, update)

        assert updated is not None
        assert updated.url == "https://new.example.com"

    def test_update_monitor_not_found(self, storage: Storage) -> None:
        """Test updating non-existent monitor."""
        update = MonitorUpdate(name="Test")
        result = storage.update_monitor("nonexistent", update)
        assert result is None

    def test_update_monitor_invalid_stage(self, storage: Storage) -> None:
        """Test updating with invalid stage."""
        data = MonitorCreate(name="Test", url="https://example.com")
        created = storage.create_monitor(data)

        update = MonitorUpdate(pipeline=[Stage(type="invalid")])
        with pytest.raises(ValueError, match="Unknown stage"):
            storage.update_monitor(created.id, update)

    def test_delete_monitor(self, storage: Storage) -> None:
        """Test deleting a monitor."""
        data = MonitorCreate(name="Test", url="https://example.com")
        created = storage.create_monitor(data)

        result = storage.delete_monitor(created.id)
        assert result is True

        monitor = storage.get_monitor(created.id)
        assert monitor is None

    def test_delete_monitor_not_found(self, storage: Storage) -> None:
        """Test deleting non-existent monitor."""
        result = storage.delete_monitor("nonexistent")
        assert result is False

    def test_delete_monitor_removes_results(self, storage: Storage) -> None:
        """Test deleting monitor also removes results."""
        data = MonitorCreate(name="Test", url="https://example.com")
        created = storage.create_monitor(data)

        # Add a result
        result = CheckResultRecord(
            id=str(uuid.uuid4()),
            monitor_id=created.id,
            status="up",
            message="OK",
            elapsed_ms=100.0,
            checked_at=datetime.now(timezone.utc),
        )
        storage.add_result(result)

        # Delete monitor
        storage.delete_monitor(created.id)

        # Results should be gone
        results = storage.get_results(created.id)
        assert results == []


class TestResultOperations:
    """Tests for result operations."""

    def test_add_result(self, storage: Storage) -> None:
        """Test adding a check result."""
        data = MonitorCreate(name="Test", url="https://example.com")
        monitor = storage.create_monitor(data)

        result = CheckResultRecord(
            id=str(uuid.uuid4()),
            monitor_id=monitor.id,
            status="up",
            message="200 OK",
            elapsed_ms=150.0,
            checked_at=datetime.now(timezone.utc),
        )
        storage.add_result(result)

        results = storage.get_results(monitor.id)
        assert len(results) == 1
        assert results[0].status == "up"

    def test_get_results_limit(self, storage: Storage) -> None:
        """Test result limit."""
        data = MonitorCreate(name="Test", url="https://example.com")
        monitor = storage.create_monitor(data)

        # Add 5 results
        for i in range(5):
            result = CheckResultRecord(
                id=str(uuid.uuid4()),
                monitor_id=monitor.id,
                status="up",
                message=f"Result {i}",
                elapsed_ms=100.0,
                checked_at=datetime.now(timezone.utc),
            )
            storage.add_result(result)

        # Get only 3
        results = storage.get_results(monitor.id, limit=3)
        assert len(results) == 3

    def test_results_sorted_by_date(self, storage: Storage) -> None:
        """Test results are sorted newest first."""
        data = MonitorCreate(name="Test", url="https://example.com")
        monitor = storage.create_monitor(data)

        # Add results with different times
        for i in range(3):
            result = CheckResultRecord(
                id=str(uuid.uuid4()),
                monitor_id=monitor.id,
                status="up",
                message=f"Result {i}",
                elapsed_ms=100.0,
                checked_at=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
            )
            storage.add_result(result)

        results = storage.get_results(monitor.id)
        # Most recent first (Jan 3)
        assert results[0].message == "Result 2"
        assert results[2].message == "Result 0"

    def test_results_retention(self, storage: Storage) -> None:
        """Test results retention limit is enforced."""
        data = MonitorCreate(name="Test", url="https://example.com")
        monitor = storage.create_monitor(data)

        # Add more results than retention limit (10)
        for i in range(15):
            result = CheckResultRecord(
                id=str(uuid.uuid4()),
                monitor_id=monitor.id,
                status="up",
                message=f"Result {i}",
                elapsed_ms=100.0,
                checked_at=datetime(2024, 1, 1, 0, i, tzinfo=timezone.utc),
            )
            storage.add_result(result)

        # Should only have 10 (retention limit)
        results = storage.get_results(monitor.id, limit=100)
        assert len(results) == 10

    def test_update_monitor_status(self, storage: Storage) -> None:
        """Test updating monitor status after check."""
        data = MonitorCreate(name="Test", url="https://example.com")
        monitor = storage.create_monitor(data)

        now = datetime.now(timezone.utc)
        storage.update_monitor_status(monitor.id, "up", now)

        updated = storage.get_monitor(monitor.id)
        assert updated is not None
        assert updated.last_status == "up"
        assert updated.last_check is not None


class TestTagOperations:
    """Tests for tag operations."""

    def test_create_monitor_with_tags(self, storage: Storage) -> None:
        """Test creating a monitor with tags."""
        data = MonitorCreate(
            name="Test",
            url="https://example.com",
            tags=["production", "api"],
        )
        monitor = storage.create_monitor(data)

        assert monitor.tags == ["production", "api"]

    def test_create_monitor_without_tags(self, storage: Storage) -> None:
        """Test creating a monitor without tags defaults to empty list."""
        data = MonitorCreate(name="Test", url="https://example.com")
        monitor = storage.create_monitor(data)

        assert monitor.tags == []

    def test_update_monitor_tags(self, storage: Storage) -> None:
        """Test updating monitor tags."""
        data = MonitorCreate(
            name="Test",
            url="https://example.com",
            tags=["old-tag"],
        )
        monitor = storage.create_monitor(data)

        update = MonitorUpdate(tags=["new-tag", "another-tag"])
        updated = storage.update_monitor(monitor.id, update)

        assert updated is not None
        assert updated.tags == ["new-tag", "another-tag"]

    def test_list_monitors_filter_by_tag(self, storage: Storage) -> None:
        """Test filtering monitors by tag."""
        # Create monitors with different tags
        storage.create_monitor(
            MonitorCreate(
                name="Prod API",
                url="https://api.example.com",
                tags=["production", "api"],
            )
        )
        storage.create_monitor(
            MonitorCreate(
                name="Staging API",
                url="https://staging.example.com",
                tags=["staging", "api"],
            )
        )
        storage.create_monitor(
            MonitorCreate(
                name="Prod Web",
                url="https://www.example.com",
                tags=["production", "web"],
            )
        )

        # Filter by tag
        prod_monitors = storage.list_monitors(tag="production")
        assert len(prod_monitors) == 2

        api_monitors = storage.list_monitors(tag="api")
        assert len(api_monitors) == 2

        staging_monitors = storage.list_monitors(tag="staging")
        assert len(staging_monitors) == 1

    def test_list_monitors_no_filter(self, storage: Storage) -> None:
        """Test listing all monitors without tag filter."""
        storage.create_monitor(
            MonitorCreate(
                name="Test 1",
                url="https://example1.com",
                tags=["tag1"],
            )
        )
        storage.create_monitor(
            MonitorCreate(
                name="Test 2",
                url="https://example2.com",
                tags=["tag2"],
            )
        )

        all_monitors = storage.list_monitors()
        assert len(all_monitors) == 2

    def test_list_tags(self, storage: Storage) -> None:
        """Test listing all unique tags."""
        storage.create_monitor(
            MonitorCreate(
                name="Test 1",
                url="https://example1.com",
                tags=["production", "api"],
            )
        )
        storage.create_monitor(
            MonitorCreate(
                name="Test 2",
                url="https://example2.com",
                tags=["staging", "api"],
            )
        )

        tags = storage.list_tags()
        assert tags == ["api", "production", "staging"]

    def test_list_tags_empty(self, storage: Storage) -> None:
        """Test listing tags when no monitors exist."""
        tags = storage.list_tags()
        assert tags == []
