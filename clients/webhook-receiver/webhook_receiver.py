#!/usr/bin/env python3
"""Simple webhook receiver that logs uptimer status changes.

This script provides a minimal HTTP server that receives webhook payloads
from uptimer and logs the status changes to the console.

Usage:
    python webhook_receiver.py [--port PORT] [--verify-signature SECRET]

Examples:
    # Start receiver on default port 8888
    python webhook_receiver.py

    # Start on custom port
    python webhook_receiver.py --port 9999

    # Verify webhook signatures
    python webhook_receiver.py --verify-signature my-webhook-secret

Then configure a webhook in uptimer pointing to:
    http://localhost:8888/webhook
"""

import argparse
import hashlib
import hmac
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhook payloads."""

    secret: str | None = None

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default logging."""
        pass

    def do_POST(self) -> None:
        """Handle POST requests to /webhook."""
        if self.path != "/webhook":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Verify signature if secret is configured
        if self.secret:
            signature_header = self.headers.get("X-Uptimer-Signature", "")
            if not signature_header.startswith("sha256="):
                self.send_error(401, "Missing or invalid signature")
                return

            expected_sig = signature_header[7:]  # Remove "sha256=" prefix
            computed_sig = hmac.new(
                self.secret.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected_sig, computed_sig):
                self.send_error(401, "Invalid signature")
                return

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        # Log the status change
        self._log_webhook(payload)

        # Send success response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "received"}')

    def _log_webhook(self, payload: dict) -> None:
        """Log webhook payload to console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event = payload.get("event", "unknown")

        if event == "status_change":
            monitor = payload.get("monitor", {})
            alert = payload.get("alert", {})

            prev_status = alert.get("previous_status", "?")
            new_status = alert.get("new_status", "?")
            monitor_name = monitor.get("name", "Unknown")
            monitor_url = monitor.get("url", "")
            message = alert.get("message", "")
            elapsed_ms = alert.get("elapsed_ms", 0)

            # Color codes for terminal
            colors = {
                "up": "\033[92m",  # Green
                "down": "\033[91m",  # Red
                "degraded": "\033[93m",  # Yellow
            }
            reset = "\033[0m"

            status_color = colors.get(new_status, "")
            print(f"\n[{timestamp}] Status Change Detected")
            print(f"  Monitor: {monitor_name}")
            print(f"  URL:     {monitor_url}")
            print(f"  Status:  {prev_status} -> {status_color}{new_status}{reset}")
            print(f"  Message: {message}")
            print(f"  Elapsed: {elapsed_ms:.1f}ms")

            tags = monitor.get("tags", [])
            if tags:
                print(f"  Tags:    {', '.join(tags)}")

        elif event == "test":
            print(f"\n[{timestamp}] Test Webhook Received")
            print("  This is a test webhook from uptimer.")

        else:
            print(f"\n[{timestamp}] Unknown Event: {event}")
            print(f"  Payload: {json.dumps(payload, indent=2)}")


def main() -> None:
    """Run the webhook receiver server."""
    parser = argparse.ArgumentParser(description="Simple webhook receiver for uptimer status changes")
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port to listen on (default: 8888)",
    )
    parser.add_argument(
        "--verify-signature",
        dest="secret",
        help="Webhook secret for signature verification",
    )
    args = parser.parse_args()

    WebhookHandler.secret = args.secret

    server = HTTPServer(("0.0.0.0", args.port), WebhookHandler)
    print(f"Webhook receiver listening on http://0.0.0.0:{args.port}/webhook")
    if args.secret:
        print("Signature verification: ENABLED")
    else:
        print("Signature verification: DISABLED")
    print("\nWaiting for webhooks... (Ctrl+C to stop)\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
