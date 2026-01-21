"""Webhook alerting for monitor status changes."""

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from uptimer.schemas import CheckResultRecord, Monitor, Webhook, WebhookDelivery
from uptimer.storage import Storage

logger = structlog.get_logger()

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds
WEBHOOK_TIMEOUT = 10.0  # seconds


def should_send_alert(previous_status: str | None, new_status: str) -> bool:
    """Determine if an alert should be sent based on status change.

    Args:
        previous_status: Previous status (None if first check)
        new_status: New status after check

    Returns:
        True if alert should be sent
    """
    # Don't alert on first check (no previous status)
    if previous_status is None:
        return False

    # Alert on any status change
    return previous_status != new_status


def build_webhook_payload(
    monitor: Monitor,
    record: CheckResultRecord,
    previous_status: str,
    new_status: str,
) -> dict[str, Any]:
    """Build the webhook payload for a status change alert.

    Args:
        monitor: The monitor that changed status
        record: The check result record
        previous_status: Previous status
        new_status: New status

    Returns:
        Webhook payload dict
    """
    return {
        "event": "status_change",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "monitor": {
            "id": monitor.id,
            "name": monitor.name,
            "url": monitor.url,
            "tags": monitor.tags,
        },
        "alert": {
            "previous_status": previous_status,
            "new_status": new_status,
            "message": record.message,
            "elapsed_ms": record.elapsed_ms,
        },
        "check": {
            "id": record.id,
            "checked_at": record.checked_at.isoformat(),
            "details": record.details,
        },
    }


def compute_signature(payload: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload.

    Args:
        payload: JSON payload string
        secret: Webhook secret

    Returns:
        Hex-encoded signature
    """
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def send_webhook(
    webhook: Webhook,
    payload: dict[str, Any],
) -> tuple[bool, int | None, str | None]:
    """Send webhook with retries.

    Args:
        webhook: Webhook configuration
        payload: Payload to send

    Returns:
        Tuple of (success, status_code, error_message)
    """
    payload_json = json.dumps(payload)

    headers = dict(webhook.headers)
    headers["Content-Type"] = "application/json"

    if webhook.secret:
        signature = compute_signature(payload_json, webhook.secret)
        headers["X-Uptimer-Signature"] = f"sha256={signature}"

    last_error: str | None = None
    last_status_code: int | None = None

    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(timeout=WEBHOOK_TIMEOUT) as client:
                response = client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers,
                )
                last_status_code = response.status_code

                if response.is_success:
                    logger.info(
                        "Webhook delivered successfully",
                        webhook_id=webhook.id,
                        webhook_name=webhook.name,
                        status_code=response.status_code,
                        attempt=attempt + 1,
                    )
                    return True, response.status_code, None

                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(
                    "Webhook delivery failed",
                    webhook_id=webhook.id,
                    webhook_name=webhook.name,
                    status_code=response.status_code,
                    attempt=attempt + 1,
                    error=last_error,
                )

        except httpx.RequestError as e:
            last_error = str(e)
            logger.warning(
                "Webhook request error",
                webhook_id=webhook.id,
                webhook_name=webhook.name,
                attempt=attempt + 1,
                error=last_error,
            )

        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAYS[attempt])

    logger.error(
        "Webhook delivery failed after all retries",
        webhook_id=webhook.id,
        webhook_name=webhook.name,
        max_retries=MAX_RETRIES,
        last_error=last_error,
    )
    return False, last_status_code, last_error


def process_alerts(
    storage: Storage,
    monitor: Monitor,
    record: CheckResultRecord,
    previous_status: str | None,
    new_status: str,
) -> None:
    """Process alerts for a monitor status change.

    This function is non-blocking - webhook failures don't affect the caller.

    Args:
        storage: Storage instance
        monitor: The monitor that was checked
        record: The check result record
        previous_status: Previous status (None if first check)
        new_status: New status after check
    """
    if not should_send_alert(previous_status, new_status):
        return

    logger.info(
        "Status change detected, processing alerts",
        monitor_id=monitor.id,
        monitor_name=monitor.name,
        previous_status=previous_status,
        new_status=new_status,
    )

    webhooks = storage.get_webhooks_for_monitor(monitor)
    if not webhooks:
        logger.debug("No webhooks configured for monitor", monitor_id=monitor.id)
        return

    payload = build_webhook_payload(monitor, record, previous_status, new_status)  # type: ignore[arg-type]

    for webhook in webhooks:
        now = datetime.now(timezone.utc)
        success, status_code, error = send_webhook(webhook, payload)

        # Record delivery
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=webhook.id,
            monitor_id=monitor.id,
            previous_status=previous_status,  # type: ignore[arg-type]
            new_status=new_status,
            success=success,
            status_code=status_code,
            error=error,
            attempted_at=now,
        )
        storage.add_webhook_delivery(delivery)

        # Update webhook last triggered
        status = "success" if success else "failed"
        storage.update_webhook_last_triggered(webhook.id, status, now)


def send_test_webhook(
    webhook: Webhook,
) -> tuple[bool, int | None, str | None]:
    """Send a test webhook payload.

    Args:
        webhook: Webhook to test

    Returns:
        Tuple of (success, status_code, error_message)
    """
    test_payload = {
        "event": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "monitor": {
            "id": "test-monitor-id",
            "name": "Test Monitor",
            "url": "https://example.com/health",
            "tags": ["test"],
        },
        "alert": {
            "previous_status": "up",
            "new_status": "down",
            "message": "This is a test webhook",
            "elapsed_ms": 100.0,
        },
        "check": {
            "id": "test-check-id",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "details": {"test": True},
        },
    }

    return send_webhook(webhook, test_payload)
