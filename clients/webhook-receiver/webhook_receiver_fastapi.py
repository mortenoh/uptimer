#!/usr/bin/env python3
"""FastAPI-based webhook receiver for uptimer status changes.

A more production-ready webhook receiver using FastAPI.

Usage:
    # Install dependencies first:
    pip install fastapi uvicorn

    # Run the server
    python webhook_receiver_fastapi.py [--port PORT] [--secret SECRET]

Examples:
    # Start on default port 8888
    python webhook_receiver_fastapi.py

    # With signature verification
    python webhook_receiver_fastapi.py --secret my-webhook-secret

    # Custom port
    python webhook_receiver_fastapi.py --port 9999

Configure a webhook in uptimer pointing to:
    http://localhost:8888/webhook
"""

import argparse
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
except ImportError:
    print("FastAPI and uvicorn are required. Install with: pip install fastapi uvicorn")
    raise SystemExit(1)

# Configuration
WEBHOOK_SECRET: str | None = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Uptimer Webhook Receiver")


def verify_signature(payload: bytes, signature_header: str) -> bool:
    """Verify webhook signature.

    Args:
        payload: Raw request body
        signature_header: X-Uptimer-Signature header value

    Returns:
        True if signature is valid
    """
    if not WEBHOOK_SECRET:
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_sig = signature_header[7:]
    computed_sig = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig, computed_sig)


def log_status_change(payload: dict[str, Any]) -> None:
    """Log status change event."""
    monitor = payload.get("monitor", {})
    alert = payload.get("alert", {})

    prev_status = alert.get("previous_status", "?")
    new_status = alert.get("new_status", "?")

    logger.info(
        "Status change: %s (%s) %s -> %s - %s (%.1fms)",
        monitor.get("name", "Unknown"),
        monitor.get("url", ""),
        prev_status,
        new_status,
        alert.get("message", ""),
        alert.get("elapsed_ms", 0),
    )


@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    """Handle webhook POST requests."""
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Uptimer-Signature", "")
    if not verify_signature(body, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")

    # Handle different event types
    event = payload.get("event", "unknown")

    if event == "status_change":
        log_status_change(payload)
    elif event == "test":
        logger.info("Test webhook received")
    else:
        logger.info("Unknown event type: %s", event)

    return JSONResponse({"status": "received"})


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"})


def main() -> None:
    """Run the webhook receiver."""
    global WEBHOOK_SECRET

    parser = argparse.ArgumentParser(description="FastAPI webhook receiver for uptimer")
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port to listen on (default: 8888)",
    )
    parser.add_argument(
        "--secret",
        help="Webhook secret for signature verification",
    )
    args = parser.parse_args()

    WEBHOOK_SECRET = args.secret

    logger.info("Starting webhook receiver on port %d", args.port)
    logger.info(
        "Signature verification: %s",
        "ENABLED" if WEBHOOK_SECRET else "DISABLED",
    )
    logger.info("Webhook endpoint: http://0.0.0.0:%d/webhook", args.port)

    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
