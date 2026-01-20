"""Tests for monitor API endpoints."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from uptimer.settings import clear_settings_cache
from uptimer.storage import Storage
from uptimer.web.api.deps import clear_storage_cache, get_storage
from uptimer.web.app import create_app


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    """Clear caches before each test."""
    clear_settings_cache()
    clear_storage_cache()


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    """Create a storage instance with temp directory."""
    return Storage(data_dir=tmp_path, results_retention=100)


@pytest.fixture
def client(storage: Storage) -> TestClient:
    """Create test client with storage override."""
    app = create_app()

    def override_storage() -> Storage:
        return storage

    app.dependency_overrides[get_storage] = override_storage

    return TestClient(app)


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    """Create authenticated test client."""
    # Login to get session
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client


class TestListMonitors:
    """Tests for GET /api/monitors."""

    def test_list_monitors_unauthorized(self, client: TestClient) -> None:
        """Test listing monitors without auth."""
        response = client.get("/api/monitors")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"

    def test_list_monitors_empty(self, auth_client: TestClient) -> None:
        """Test listing monitors when empty."""
        response = auth_client.get("/api/monitors")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_monitors(self, auth_client: TestClient) -> None:
        """Test listing monitors."""
        # Create a monitor first
        auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )

        response = auth_client.get("/api/monitors")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test"


class TestCreateMonitor:
    """Tests for POST /api/monitors."""

    def test_create_monitor_unauthorized(self, client: TestClient) -> None:
        """Test creating monitor without auth."""
        response = client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        assert response.status_code == 401

    def test_create_monitor_minimal(self, auth_client: TestClient) -> None:
        """Test creating monitor with minimal fields."""
        response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test"
        assert data["url"] == "https://example.com"
        assert data["checker"] == "http"
        assert data["interval"] == 60
        assert data["enabled"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_monitor_full(self, auth_client: TestClient) -> None:
        """Test creating monitor with all fields."""
        response = auth_client.post(
            "/api/monitors",
            json={
                "name": "Full Monitor",
                "url": "https://api.example.com",
                "checker": "http",
                "username": "user",
                "password": "pass",
                "interval": 120,
                "enabled": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Full Monitor"
        assert data["interval"] == 120
        assert data["enabled"] is False

    def test_create_monitor_url_normalized(self, auth_client: TestClient) -> None:
        """Test URL is normalized."""
        response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "example.com"},
        )
        assert response.status_code == 201
        assert response.json()["url"] == "https://example.com"

    def test_create_monitor_invalid_checker(self, auth_client: TestClient) -> None:
        """Test creating monitor with invalid checker."""
        response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com", "checker": "invalid"},
        )
        assert response.status_code == 422
        assert "Unknown checker" in response.json()["detail"]

    def test_create_monitor_invalid_interval(self, auth_client: TestClient) -> None:
        """Test creating monitor with interval < 10."""
        response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com", "interval": 5},
        )
        assert response.status_code == 422


class TestGetMonitor:
    """Tests for GET /api/monitors/{id}."""

    def test_get_monitor_unauthorized(self, client: TestClient) -> None:
        """Test getting monitor without auth."""
        response = client.get("/api/monitors/some-id")
        assert response.status_code == 401

    def test_get_monitor(self, auth_client: TestClient) -> None:
        """Test getting a monitor."""
        # Create first
        create_response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        monitor_id = create_response.json()["id"]

        response = auth_client.get(f"/api/monitors/{monitor_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    def test_get_monitor_not_found(self, auth_client: TestClient) -> None:
        """Test getting non-existent monitor."""
        response = auth_client.get("/api/monitors/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Monitor not found"


class TestUpdateMonitor:
    """Tests for PUT /api/monitors/{id}."""

    def test_update_monitor_unauthorized(self, client: TestClient) -> None:
        """Test updating monitor without auth."""
        response = client.put(
            "/api/monitors/some-id",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    def test_update_monitor(self, auth_client: TestClient) -> None:
        """Test updating a monitor."""
        # Create first
        create_response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        monitor_id = create_response.json()["id"]

        response = auth_client.put(
            f"/api/monitors/{monitor_id}",
            json={"name": "Updated", "interval": 300},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["interval"] == 300
        assert data["url"] == "https://example.com"

    def test_update_monitor_not_found(self, auth_client: TestClient) -> None:
        """Test updating non-existent monitor."""
        response = auth_client.put(
            "/api/monitors/nonexistent",
            json={"name": "Updated"},
        )
        assert response.status_code == 404

    def test_update_monitor_invalid_checker(self, auth_client: TestClient) -> None:
        """Test updating with invalid checker."""
        # Create first
        create_response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        monitor_id = create_response.json()["id"]

        response = auth_client.put(
            f"/api/monitors/{monitor_id}",
            json={"checker": "invalid"},
        )
        assert response.status_code == 422


class TestDeleteMonitor:
    """Tests for DELETE /api/monitors/{id}."""

    def test_delete_monitor_unauthorized(self, client: TestClient) -> None:
        """Test deleting monitor without auth."""
        response = client.delete("/api/monitors/some-id")
        assert response.status_code == 401

    def test_delete_monitor(self, auth_client: TestClient) -> None:
        """Test deleting a monitor."""
        # Create first
        create_response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        monitor_id = create_response.json()["id"]

        response = auth_client.delete(f"/api/monitors/{monitor_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = auth_client.get(f"/api/monitors/{monitor_id}")
        assert get_response.status_code == 404

    def test_delete_monitor_not_found(self, auth_client: TestClient) -> None:
        """Test deleting non-existent monitor."""
        response = auth_client.delete("/api/monitors/nonexistent")
        assert response.status_code == 404


class TestRunCheck:
    """Tests for POST /api/monitors/{id}/check."""

    def test_run_check_unauthorized(self, client: TestClient) -> None:
        """Test running check without auth."""
        response = client.post("/api/monitors/some-id/check")
        assert response.status_code == 401

    def test_run_check_not_found(self, auth_client: TestClient) -> None:
        """Test running check on non-existent monitor."""
        response = auth_client.post("/api/monitors/nonexistent/check")
        assert response.status_code == 404

    def test_run_check(self, auth_client: TestClient) -> None:
        """Test running a check."""
        # Create monitor
        create_response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://httpbin.org/status/200"},
        )
        monitor_id = create_response.json()["id"]

        response = auth_client.post(f"/api/monitors/{monitor_id}/check")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "up"
        assert data["monitor_id"] == monitor_id
        assert "elapsed_ms" in data
        assert "checked_at" in data

    def test_run_check_with_mock(self, auth_client: TestClient) -> None:
        """Test running a check with mocked checker."""
        from uptimer.checkers.base import CheckResult, Status

        # Create monitor
        create_response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        monitor_id = create_response.json()["id"]

        # Mock the checker
        mock_result = CheckResult(
            status=Status.UP,
            url="https://example.com",
            message="200 OK",
            elapsed_ms=150.0,
            details={"status_code": 200},
        )
        mock_checker = MagicMock()
        mock_checker.check.return_value = mock_result

        with patch("uptimer.web.api.monitors.get_checker") as mock_get:
            mock_get.return_value = lambda: mock_checker
            response = auth_client.post(f"/api/monitors/{monitor_id}/check")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "up"
        assert data["message"] == "200 OK"


class TestGetResults:
    """Tests for GET /api/monitors/{id}/results."""

    def test_get_results_unauthorized(self, client: TestClient) -> None:
        """Test getting results without auth."""
        response = client.get("/api/monitors/some-id/results")
        assert response.status_code == 401

    def test_get_results_not_found(self, auth_client: TestClient) -> None:
        """Test getting results for non-existent monitor."""
        response = auth_client.get("/api/monitors/nonexistent/results")
        assert response.status_code == 404

    def test_get_results_empty(self, auth_client: TestClient) -> None:
        """Test getting results when empty."""
        # Create monitor
        create_response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        monitor_id = create_response.json()["id"]

        response = auth_client.get(f"/api/monitors/{monitor_id}/results")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_results_with_limit(self, auth_client: TestClient) -> None:
        """Test getting results with limit parameter."""
        from uptimer.checkers.base import CheckResult, Status

        # Create monitor
        create_response = auth_client.post(
            "/api/monitors",
            json={"name": "Test", "url": "https://example.com"},
        )
        monitor_id = create_response.json()["id"]

        # Run a few checks with mock
        mock_result = CheckResult(
            status=Status.UP,
            url="https://example.com",
            message="OK",
            elapsed_ms=100.0,
            details={},
        )
        mock_checker = MagicMock()
        mock_checker.check.return_value = mock_result

        with patch("uptimer.web.api.monitors.get_checker") as mock_get:
            mock_get.return_value = lambda: mock_checker
            for _ in range(5):
                auth_client.post(f"/api/monitors/{monitor_id}/check")

        # Get with limit
        response = auth_client.get(f"/api/monitors/{monitor_id}/results?limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3
