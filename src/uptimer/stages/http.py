"""HTTP stage - follows redirects and checks final status."""

import time

import httpx

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status


class HttpStage(Stage):
    """HTTP stage that follows redirects."""

    name = "http"
    description = "HTTP check with redirect following"
    is_network_stage = True

    # User-Agent to avoid being blocked by sites that reject bot traffic
    USER_AGENT = "Mozilla/5.0 (compatible; Uptimer/1.0; +https://github.com/mortenoh/uptimer)"

    def __init__(self, timeout: float = 10.0, headers: dict[str, str] | None = None) -> None:
        """Initialize with timeout and optional custom headers.

        Args:
            timeout: Request timeout in seconds
            headers: Custom HTTP headers to send with the request
        """
        self.timeout = timeout
        self.custom_headers = headers or {}

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check URL via HTTP GET, following redirects."""
        # Add https:// if no protocol specified
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        details: dict[str, object] = {}

        try:
            start = time.perf_counter()
            headers = {"User-Agent": self.USER_AGENT, **self.custom_headers}
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
                elapsed_ms = (time.perf_counter() - start) * 1000

                # Determine status
                if response.status_code < 400:
                    status = Status.UP
                else:
                    status = Status.DEGRADED

                # Build details
                details["status_code"] = response.status_code
                details["http_version"] = response.http_version
                details["final_url"] = str(response.url)

                if response.headers.get("server"):
                    details["server"] = response.headers["server"]
                if response.headers.get("content-type"):
                    details["content_type"] = response.headers["content-type"]

                # Redirect chain
                if response.history:
                    details["redirects"] = [
                        {"status": r.status_code, "location": r.headers.get("location", "")} for r in response.history
                    ]

                # Store response data in context for subsequent stages
                if context is not None:
                    context.response_body = response.text
                    context.response_headers = dict(response.headers)
                    context.status_code = response.status_code
                    context.elapsed_ms = elapsed_ms

                return CheckResult(
                    status=status,
                    url=url,
                    message=str(response.status_code),
                    elapsed_ms=elapsed_ms,
                    details=details,
                )

        except httpx.RequestError as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=e.__class__.__name__,
                details={"error": str(e)},
            )
