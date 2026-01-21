"""Tests for webhook API endpoints."""

from typing import Any
from unittest.mock import patch

import mongomock
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

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
def storage() -> Storage:
    """Create a storage instance with mongomock."""
    client: MongoClient[dict[str, Any]] = mongomock.MongoClient()
    return Storage(
        mongodb_uri="mongodb://localhost:27017",
        mongodb_db="test_uptimer",
        results_retention=100,
        client=client,
    )


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
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client


class TestListWebhooks:
    """Tests for GET /api/webhooks."""

    def test_list_webhooks_unauthorized(self, client: TestClient) -> None:
        """Test listing webhooks without auth."""
        response = client.get("/api/webhooks")
        assert response.status_code == 401

    def test_list_webhooks_empty(self, auth_client: TestClient) -> None:
        """Test listing webhooks when empty."""
        response = auth_client.get("/api/webhooks")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_webhooks(self, auth_client: TestClient) -> None:
        """Test listing webhooks."""
        auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )

        response = auth_client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test"


class TestCreateWebhook:
    """Tests for POST /api/webhooks."""

    def test_create_webhook_unauthorized(self, client: TestClient) -> None:
        """Test creating webhook without auth."""
        response = client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        assert response.status_code == 401

    def test_create_webhook_minimal(self, auth_client: TestClient) -> None:
        """Test creating webhook with minimal fields."""
        response = auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test"
        assert data["url"] == "https://example.com/webhook"
        assert data["enabled"] is True
        assert data["monitor_ids"] == []
        assert data["tags"] == []
        assert data["secret"] is None
        assert data["headers"] == {}
        assert "id" in data
        assert "created_at" in data

    def test_create_webhook_full(self, auth_client: TestClient) -> None:
        """Test creating webhook with all fields."""
        response = auth_client.post(
            "/api/webhooks",
            json={
                "name": "Full Webhook",
                "url": "https://webhook.example.com/notify",
                "enabled": False,
                "monitor_ids": ["mon-1", "mon-2"],
                "tags": ["production"],
                "secret": "my-secret",
                "headers": {"X-Custom": "value"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Full Webhook"
        assert data["url"] == "https://webhook.example.com/notify"
        assert data["enabled"] is False
        assert data["monitor_ids"] == ["mon-1", "mon-2"]
        assert data["tags"] == ["production"]
        assert data["secret"] == "my-secret"
        assert data["headers"] == {"X-Custom": "value"}

    def test_create_webhook_empty_name(self, auth_client: TestClient) -> None:
        """Test creating webhook with empty name fails."""
        response = auth_client.post(
            "/api/webhooks",
            json={"name": "  ", "url": "https://example.com/webhook"},
        )
        assert response.status_code == 422


class TestGetWebhook:
    """Tests for GET /api/webhooks/{id}."""

    def test_get_webhook_unauthorized(self, client: TestClient) -> None:
        """Test getting webhook without auth."""
        response = client.get("/api/webhooks/some-id")
        assert response.status_code == 401

    def test_get_webhook(self, auth_client: TestClient) -> None:
        """Test getting a webhook."""
        create_response = auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        webhook_id = create_response.json()["id"]

        response = auth_client.get(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    def test_get_webhook_not_found(self, auth_client: TestClient) -> None:
        """Test getting non-existent webhook."""
        response = auth_client.get("/api/webhooks/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Webhook not found"


class TestUpdateWebhook:
    """Tests for PUT /api/webhooks/{id}."""

    def test_update_webhook_unauthorized(self, client: TestClient) -> None:
        """Test updating webhook without auth."""
        response = client.put(
            "/api/webhooks/some-id",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    def test_update_webhook(self, auth_client: TestClient) -> None:
        """Test updating a webhook."""
        create_response = auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        webhook_id = create_response.json()["id"]

        response = auth_client.put(
            f"/api/webhooks/{webhook_id}",
            json={"name": "Updated", "enabled": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["enabled"] is False
        assert data["url"] == "https://example.com/webhook"

    def test_update_webhook_not_found(self, auth_client: TestClient) -> None:
        """Test updating non-existent webhook."""
        response = auth_client.put(
            "/api/webhooks/nonexistent",
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteWebhook:
    """Tests for DELETE /api/webhooks/{id}."""

    def test_delete_webhook_unauthorized(self, client: TestClient) -> None:
        """Test deleting webhook without auth."""
        response = client.delete("/api/webhooks/some-id")
        assert response.status_code == 401

    def test_delete_webhook(self, auth_client: TestClient) -> None:
        """Test deleting a webhook."""
        create_response = auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        webhook_id = create_response.json()["id"]

        response = auth_client.delete(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 204

        get_response = auth_client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.status_code == 404

    def test_delete_webhook_not_found(self, auth_client: TestClient) -> None:
        """Test deleting non-existent webhook."""
        response = auth_client.delete("/api/webhooks/nonexistent")
        assert response.status_code == 404


class TestTestWebhook:
    """Tests for POST /api/webhooks/{id}/test."""

    def test_test_webhook_unauthorized(self, client: TestClient) -> None:
        """Test testing webhook without auth."""
        response = client.post("/api/webhooks/some-id/test")
        assert response.status_code == 401

    def test_test_webhook_not_found(self, auth_client: TestClient) -> None:
        """Test testing non-existent webhook."""
        response = auth_client.post("/api/webhooks/nonexistent/test")
        assert response.status_code == 404

    def test_test_webhook_success(self, auth_client: TestClient) -> None:
        """Test testing a webhook with successful response."""
        create_response = auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        webhook_id = create_response.json()["id"]

        with patch("uptimer.alerting.httpx.Client") as mock_client:
            from unittest.mock import MagicMock

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            response = auth_client.post(f"/api/webhooks/{webhook_id}/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status_code"] == 200
        assert data["error"] is None

    def test_test_webhook_failure(self, auth_client: TestClient) -> None:
        """Test testing a webhook with failed response."""
        create_response = auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        webhook_id = create_response.json()["id"]

        with patch("uptimer.alerting.httpx.Client") as mock_client:
            from unittest.mock import MagicMock

            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.is_success = False
            mock_response.text = "Server Error"
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with patch("uptimer.alerting.time.sleep"):  # Skip retry delays
                response = auth_client.post(f"/api/webhooks/{webhook_id}/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status_code"] == 500
        assert "HTTP 500" in data["error"]


class TestWebhookDeliveries:
    """Tests for GET /api/webhooks/{id}/deliveries."""

    def test_get_deliveries_unauthorized(self, client: TestClient) -> None:
        """Test getting deliveries without auth."""
        response = client.get("/api/webhooks/some-id/deliveries")
        assert response.status_code == 401

    def test_get_deliveries_not_found(self, auth_client: TestClient) -> None:
        """Test getting deliveries for non-existent webhook."""
        response = auth_client.get("/api/webhooks/nonexistent/deliveries")
        assert response.status_code == 404

    def test_get_deliveries_empty(self, auth_client: TestClient) -> None:
        """Test getting deliveries when none exist."""
        create_response = auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        webhook_id = create_response.json()["id"]

        response = auth_client.get(f"/api/webhooks/{webhook_id}/deliveries")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_deliveries_with_limit(self, auth_client: TestClient, storage: Storage) -> None:
        """Test getting deliveries with limit."""
        import uuid
        from datetime import datetime, timezone

        from uptimer.schemas import WebhookDelivery

        create_response = auth_client.post(
            "/api/webhooks",
            json={"name": "Test", "url": "https://example.com/webhook"},
        )
        webhook_id = create_response.json()["id"]

        # Add some deliveries directly
        for _ in range(5):
            delivery = WebhookDelivery(
                id=str(uuid.uuid4()),
                webhook_id=webhook_id,
                monitor_id="mon-1",
                previous_status="up",
                new_status="down",
                success=True,
                attempted_at=datetime.now(timezone.utc),
            )
            storage.add_webhook_delivery(delivery)

        response = auth_client.get(f"/api/webhooks/{webhook_id}/deliveries?limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3
