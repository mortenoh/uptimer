"""TCP checker - checks if a port is open and responding."""

import socket
import time
from urllib.parse import urlparse

from uptimer.checkers.base import CheckContext, Checker, CheckResult, Status
from uptimer.checkers.registry import register_checker


@register_checker
class TcpChecker(Checker):
    """Check if a TCP port is open and responding."""

    name = "tcp"
    description = "Check TCP port connectivity"
    is_network_checker = True

    def __init__(self, port: int | None = None, timeout: float = 10.0) -> None:
        """Initialize TCP checker.

        Args:
            port: Port to check (defaults to 80 or 443 based on URL scheme)
            timeout: Connection timeout in seconds
        """
        self.port = port
        self.timeout = timeout

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check TCP connectivity to host:port."""
        # Parse URL to get hostname
        if not url.startswith(("http://", "https://", "tcp://")):
            url = f"https://{url}"

        parsed = urlparse(url)
        hostname = parsed.hostname

        # Determine port
        if self.port:
            port = self.port
        elif parsed.port:
            port = parsed.port
        elif parsed.scheme == "https":
            port = 443
        else:
            port = 80

        if not hostname:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="Invalid URL: no hostname",
                details={"error": "Could not parse hostname from URL"},
            )

        try:
            start = time.perf_counter()
            sock = socket.create_connection((hostname, port), timeout=self.timeout)
            elapsed_ms = (time.perf_counter() - start) * 1000
            sock.close()

            return CheckResult(
                status=Status.UP,
                url=url,
                message=f"Port {port} open ({elapsed_ms:.1f}ms)",
                elapsed_ms=elapsed_ms,
                details={
                    "hostname": hostname,
                    "port": port,
                    "connect_time_ms": elapsed_ms,
                },
            )

        except socket.timeout:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Port {port} timeout",
                details={
                    "hostname": hostname,
                    "port": port,
                    "error": "Connection timeout",
                },
            )
        except socket.error as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                msg = f"Port {port} refused"
            elif "No route to host" in error_msg:
                msg = f"No route to {hostname}"
            else:
                msg = f"Port {port} error: {error_msg}"

            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=msg,
                details={
                    "hostname": hostname,
                    "port": port,
                    "error": error_msg,
                },
            )
