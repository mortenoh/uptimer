"""Webhook API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from uptimer.alerting import send_test_webhook
from uptimer.schemas import Webhook, WebhookCreate, WebhookDelivery, WebhookUpdate
from uptimer.storage import Storage
from uptimer.web.api.deps import get_storage, require_auth

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class TestWebhookResponse(BaseModel):
    """Response for test webhook endpoint."""

    success: bool
    status_code: int | None = None
    error: str | None = None


@router.get("", response_model=list[Webhook])
async def list_webhooks(
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> list[Webhook]:
    """List all webhooks."""
    return storage.list_webhooks()


@router.post("", response_model=Webhook, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreate,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> Webhook:
    """Create a new webhook."""
    return storage.create_webhook(data)


@router.get("/{webhook_id}", response_model=Webhook)
async def get_webhook(
    webhook_id: str,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> Webhook:
    """Get a webhook by ID."""
    webhook = storage.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )
    return webhook


@router.put("/{webhook_id}", response_model=Webhook)
async def update_webhook(
    webhook_id: str,
    data: WebhookUpdate,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> Webhook:
    """Update a webhook."""
    webhook = storage.update_webhook(webhook_id, data)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> None:
    """Delete a webhook."""
    deleted = storage.delete_webhook(webhook_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )


@router.post("/{webhook_id}/test", response_model=TestWebhookResponse)
async def test_webhook(
    webhook_id: str,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> TestWebhookResponse:
    """Send a test payload to the webhook."""
    webhook = storage.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    success, status_code, error = send_test_webhook(webhook)
    return TestWebhookResponse(
        success=success,
        status_code=status_code,
        error=error,
    )


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDelivery])
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> list[WebhookDelivery]:
    """Get delivery history for a webhook."""
    webhook = storage.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )
    return storage.get_webhook_deliveries(webhook_id, limit=limit)
