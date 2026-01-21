"""SSL stage - validates SSL/TLS certificates."""

import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


@register_stage
class SslStage(Stage):
    """Check SSL certificate validity and expiration."""

    name = "ssl"
    description = "Check SSL certificate validity and expiration"
    is_network_stage = True

    def __init__(self, warn_days: int = 30, timeout: float = 10.0) -> None:
        """Initialize SSL stage.

        Args:
            warn_days: Days before expiry to warn (returns DEGRADED)
            timeout: Connection timeout in seconds
        """
        self.warn_days = warn_days
        self.timeout = timeout

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check SSL certificate for the given URL."""
        # Parse URL to get hostname
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or 443

        if not hostname:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="Invalid URL: no hostname",
                details={"error": "Could not parse hostname from URL"},
            )

        try:
            # Create SSL context
            ctx = ssl.create_default_context()

            with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

            if not cert:
                return CheckResult(
                    status=Status.DOWN,
                    url=url,
                    message="No certificate returned",
                    details={"hostname": hostname, "port": port},
                )

            # Parse certificate info
            not_after_str = str(cert.get("notAfter", ""))
            not_before_str = str(cert.get("notBefore", ""))

            # Extract subject/issuer CN from nested tuple structure
            subject_cn = ""
            issuer_cn = ""
            for item in cert.get("subject", ()):
                if len(item) > 0:
                    kv = item[0] if len(item[0]) == 2 else item
                    if len(kv) >= 2 and kv[0] == "commonName":
                        subject_cn = str(kv[1])
            for item in cert.get("issuer", ()):
                if len(item) > 0:
                    kv = item[0] if len(item[0]) == 2 else item
                    if len(kv) >= 2 and kv[0] == "commonName":
                        issuer_cn = str(kv[1])

            # Parse expiry date
            not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            not_before = datetime.strptime(not_before_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            days_until_expiry = (not_after - now).days

            details = {
                "hostname": hostname,
                "port": port,
                "subject_cn": subject_cn,
                "issuer_cn": issuer_cn,
                "not_before": not_before.isoformat(),
                "not_after": not_after.isoformat(),
                "days_until_expiry": days_until_expiry,
                "serial_number": str(cert.get("serialNumber", "")),
            }

            # Check expiry
            if days_until_expiry < 0:
                return CheckResult(
                    status=Status.DOWN,
                    url=url,
                    message=f"Certificate expired {abs(days_until_expiry)} days ago",
                    details=details,
                )

            if days_until_expiry <= self.warn_days:
                return CheckResult(
                    status=Status.DEGRADED,
                    url=url,
                    message=f"Certificate expires in {days_until_expiry} days",
                    details=details,
                )

            return CheckResult(
                status=Status.UP,
                url=url,
                message=f"Valid, expires in {days_until_expiry} days",
                details=details,
            )

        except ssl.SSLError as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"SSL error: {e.reason}",
                details={"hostname": hostname, "port": port, "error": str(e)},
            )
        except socket.timeout:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="Connection timeout",
                details={"hostname": hostname, "port": port, "error": "timeout"},
            )
        except socket.error as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Connection failed: {e}",
                details={"hostname": hostname, "port": port, "error": str(e)},
            )
