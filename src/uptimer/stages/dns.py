"""DNS stage - validates DNS resolution."""

import socket
import time
from urllib.parse import urlparse

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


@register_stage
class DnsStage(Stage):
    """Check DNS resolution for a hostname."""

    name = "dns"
    description = "Check DNS resolution"
    is_network_stage = True

    def __init__(self, expected_ip: str | None = None) -> None:
        """Initialize DNS stage.

        Args:
            expected_ip: Expected IP address (optional validation)
        """
        self.expected_ip = expected_ip

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check DNS resolution for the hostname in the URL."""
        # Parse URL to get hostname
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="Invalid URL: no hostname",
                details={"error": "Could not parse hostname from URL"},
            )

        try:
            start = time.perf_counter()
            # Get all IP addresses
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Extract unique IP addresses
            ips = list(set(str(addr[4][0]) for addr in addr_info))
            ipv4 = [ip for ip in ips if ":" not in ip]
            ipv6 = [ip for ip in ips if ":" in ip]

            details = {
                "hostname": hostname,
                "ipv4": ipv4,
                "ipv6": ipv6,
                "resolve_time_ms": elapsed_ms,
            }

            # Validate expected IP if specified
            if self.expected_ip:
                if self.expected_ip in ips:
                    return CheckResult(
                        status=Status.UP,
                        url=url,
                        message=f"Resolved to {self.expected_ip} (expected)",
                        elapsed_ms=elapsed_ms,
                        details=details,
                    )
                else:
                    return CheckResult(
                        status=Status.DOWN,
                        url=url,
                        message=f"Expected {self.expected_ip}, got {ips}",
                        elapsed_ms=elapsed_ms,
                        details=details,
                    )

            # No expected IP, just report resolution
            primary_ip = ipv4[0] if ipv4 else (ipv6[0] if ipv6 else "unknown")
            return CheckResult(
                status=Status.UP,
                url=url,
                message=f"Resolved to {primary_ip}",
                elapsed_ms=elapsed_ms,
                details=details,
            )

        except socket.gaierror as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"DNS resolution failed: {e.strerror}",
                details={"hostname": hostname, "error": str(e)},
            )
        except socket.herror as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Host error: {e.strerror}",
                details={"hostname": hostname, "error": str(e)},
            )
