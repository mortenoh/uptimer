"""Tests for alerting module."""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import mongomock
import pytest
from pymongo import MongoClient

from uptimer.alerting import (
    build_webhook_payload,
    compute_signature,
    process_alerts,
    send_test_webhook,
    send_webhook,
    should_send_alert,
)
from uptimer.schemas import (
    CheckResultRecord,
    Monitor,
    MonitorCreate,
    Webhook,
    WebhookCreate,
)
from uptimer.storage import Storage


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
def monitor(storage: Storage) -> Monitor:
    """Create a test monitor."""
    data = MonitorCreate(
        name="Test Monitor",
        url="https://example.com",
        tags=["production", "api"],
    )
    return storage.create_monitor(data)


@pytest.fixture
def webhook(storage: Storage) -> Webhook:
    """Create a test webhook."""
    data = WebhookCreate(
        name="Test Webhook",
        url="https://webhook.example.com/notify",
        enabled=True,
    )
    return storage.create_webhook(data)


@pytest.fixture
def check_result(monitor: Monitor) -> CheckResultRecord:
    """Create a test check result."""
    return CheckResultRecord(
        id=str(uuid.uuid4()),
        monitor_id=monitor.id,
        status="down",
        message="HTTP 503 Service Unavailable",
        elapsed_ms=1523.4,
        details={"status_code": 503},
        checked_at=datetime.now(timezone.utc),
    )


class TestShouldSendAlert:
    """Tests for should_send_alert function."""

    def test_no_alert_on_first_check(self) -> None:
        """Test no alert when previous status is None."""
        assert should_send_alert(None, "up") is False
        assert should_send_alert(None, "down") is False

    def test_alert_on_status_change(self) -> None:
        """Test alert is sent on status change."""
        assert should_send_alert("up", "down") is True
        assert should_send_alert("down", "up") is True
        assert should_send_alert("up", "degraded") is True

    def test_no_alert_on_same_status(self) -> None:
        """Test no alert when status unchanged."""
        assert should_send_alert("up", "up") is False
        assert should_send_alert("down", "down") is False


class TestBuildWebhookPayload:
    """Tests for build_webhook_payload function."""

    def test_payload_structure(self, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test payload has correct structure."""
        payload = build_webhook_payload(monitor, check_result, "up", "down")

        assert payload["event"] == "status_change"
        assert "timestamp" in payload
        assert payload["monitor"]["id"] == monitor.id
        assert payload["monitor"]["name"] == monitor.name
        assert payload["monitor"]["url"] == monitor.url
        assert payload["monitor"]["tags"] == monitor.tags
        assert payload["alert"]["previous_status"] == "up"
        assert payload["alert"]["new_status"] == "down"
        assert payload["alert"]["message"] == check_result.message
        assert payload["alert"]["elapsed_ms"] == check_result.elapsed_ms
        assert payload["check"]["id"] == check_result.id
        assert "checked_at" in payload["check"]
        assert payload["check"]["details"] == check_result.details


class TestComputeSignature:
    """Tests for compute_signature function."""

    def test_signature_is_hex(self) -> None:
        """Test signature is hex encoded."""
        sig = compute_signature('{"test": true}', "secret")
        assert all(c in "0123456789abcdef" for c in sig)

    def test_signature_is_consistent(self) -> None:
        """Test same payload and secret produce same signature."""
        payload = '{"event": "test"}'
        secret = "my-secret"
        sig1 = compute_signature(payload, secret)
        sig2 = compute_signature(payload, secret)
        assert sig1 == sig2

    def test_different_secrets_different_signatures(self) -> None:
        """Test different secrets produce different signatures."""
        payload = '{"event": "test"}'
        sig1 = compute_signature(payload, "secret1")
        sig2 = compute_signature(payload, "secret2")
        assert sig1 != sig2


class TestSendWebhook:
    """Tests for send_webhook function."""

    def test_successful_delivery(self, webhook: Webhook) -> None:
        """Test successful webhook delivery."""
        payload = {"event": "test"}

        with patch("uptimer.alerting.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            success, status_code, error = send_webhook(webhook, payload)

        assert success is True
        assert status_code == 200
        assert error is None

    def test_failed_delivery_http_error(self, webhook: Webhook) -> None:
        """Test webhook delivery with HTTP error."""
        payload = {"event": "test"}

        with patch("uptimer.alerting.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.is_success = False
            mock_response.text = "Internal Server Error"
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with patch("uptimer.alerting.time.sleep"):  # Skip retry delays
                success, status_code, error = send_webhook(webhook, payload)

        assert success is False
        assert status_code == 500
        assert "HTTP 500" in error  # type: ignore[operator]

    def test_includes_signature_header(self) -> None:
        """Test signature header is included when secret is set."""
        webhook = Webhook(
            id="test-id",
            name="Test",
            url="https://example.com/webhook",
            enabled=True,
            secret="my-secret",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        payload = {"event": "test"}

        with patch("uptimer.alerting.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            send_webhook(webhook, payload)

            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            headers = call_args.kwargs["headers"]
            assert "X-Uptimer-Signature" in headers
            assert headers["X-Uptimer-Signature"].startswith("sha256=")

    def test_custom_headers_included(self) -> None:
        """Test custom headers are included."""
        webhook = Webhook(
            id="test-id",
            name="Test",
            url="https://example.com/webhook",
            enabled=True,
            headers={"X-Custom": "value"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        payload = {"event": "test"}

        with patch("uptimer.alerting.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            send_webhook(webhook, payload)

            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            headers = call_args.kwargs["headers"]
            assert headers["X-Custom"] == "value"


class TestProcessAlerts:
    """Tests for process_alerts function."""

    def test_no_alert_on_first_check(self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test no webhooks are called on first check."""
        # Create webhook
        storage.create_webhook(WebhookCreate(name="Test", url="https://example.com"))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            process_alerts(storage, monitor, check_result, None, "up")
            mock_send.assert_not_called()

    def test_no_alert_on_same_status(self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test no webhooks are called when status unchanged."""
        storage.create_webhook(WebhookCreate(name="Test", url="https://example.com"))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            process_alerts(storage, monitor, check_result, "up", "up")
            mock_send.assert_not_called()

    def test_alert_on_status_change(self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test webhook is called on status change."""
        storage.create_webhook(WebhookCreate(name="Test", url="https://example.com"))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            mock_send.return_value = (True, 200, None)
            process_alerts(storage, monitor, check_result, "up", "down")
            mock_send.assert_called_once()

    def test_delivery_recorded(self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test webhook delivery is recorded."""
        webhook = storage.create_webhook(WebhookCreate(name="Test", url="https://example.com"))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            mock_send.return_value = (True, 200, None)
            process_alerts(storage, monitor, check_result, "up", "down")

        deliveries = storage.get_webhook_deliveries(webhook.id)
        assert len(deliveries) == 1
        assert deliveries[0].success is True
        assert deliveries[0].monitor_id == monitor.id
        assert deliveries[0].previous_status == "up"
        assert deliveries[0].new_status == "down"

    def test_failed_delivery_recorded(
        self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord
    ) -> None:
        """Test failed delivery is recorded."""
        webhook = storage.create_webhook(WebhookCreate(name="Test", url="https://example.com"))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            mock_send.return_value = (False, 500, "Server error")
            process_alerts(storage, monitor, check_result, "up", "down")

        deliveries = storage.get_webhook_deliveries(webhook.id)
        assert len(deliveries) == 1
        assert deliveries[0].success is False
        assert deliveries[0].error == "Server error"


class TestWebhookFiltering:
    """Tests for webhook filtering by monitor ID and tags."""

    def test_webhook_matches_by_id(self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test webhook matches when monitor_ids includes monitor."""
        storage.create_webhook(WebhookCreate(name="Specific", url="https://example.com", monitor_ids=[monitor.id]))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            mock_send.return_value = (True, 200, None)
            process_alerts(storage, monitor, check_result, "up", "down")
            mock_send.assert_called_once()

    def test_webhook_excluded_by_id(self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test webhook excluded when monitor_ids doesn't include monitor."""
        storage.create_webhook(WebhookCreate(name="Other", url="https://example.com", monitor_ids=["other-id"]))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            process_alerts(storage, monitor, check_result, "up", "down")
            mock_send.assert_not_called()

    def test_webhook_matches_by_tag(self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test webhook matches when tags overlap."""
        storage.create_webhook(WebhookCreate(name="Tagged", url="https://example.com", tags=["production"]))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            mock_send.return_value = (True, 200, None)
            process_alerts(storage, monitor, check_result, "up", "down")
            mock_send.assert_called_once()

    def test_webhook_excluded_by_tag(self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord) -> None:
        """Test webhook excluded when tags don't overlap."""
        storage.create_webhook(WebhookCreate(name="Staging", url="https://example.com", tags=["staging"]))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            process_alerts(storage, monitor, check_result, "up", "down")
            mock_send.assert_not_called()

    def test_webhook_matches_all_monitors(
        self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord
    ) -> None:
        """Test webhook with no filters matches all monitors."""
        storage.create_webhook(WebhookCreate(name="Global", url="https://example.com"))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            mock_send.return_value = (True, 200, None)
            process_alerts(storage, monitor, check_result, "up", "down")
            mock_send.assert_called_once()

    def test_disabled_webhook_not_called(
        self, storage: Storage, monitor: Monitor, check_result: CheckResultRecord
    ) -> None:
        """Test disabled webhook is not called."""
        storage.create_webhook(WebhookCreate(name="Disabled", url="https://example.com", enabled=False))

        with patch("uptimer.alerting.send_webhook") as mock_send:
            process_alerts(storage, monitor, check_result, "up", "down")
            mock_send.assert_not_called()


class TestSendTestWebhook:
    """Tests for send_test_webhook function."""

    def test_sends_test_payload(self, webhook: Webhook) -> None:
        """Test test webhook sends correct payload."""
        with patch("uptimer.alerting.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            success, status_code, error = send_test_webhook(webhook)

            assert success is True
            assert status_code == 200
            assert error is None

            # Verify payload contains test event
            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            import json

            payload = json.loads(call_args.kwargs["content"])
            assert payload["event"] == "test"
            assert payload["monitor"]["name"] == "Test Monitor"
