"""DHIS2 stage - checks DHIS2 instance health with authentication."""

import time

import httpx

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


@register_stage
class Dhis2Stage(Stage):
    """DHIS2 health stage with basic authentication."""

    name = "dhis2"
    description = "DHIS2 instance check with authentication"
    is_network_stage = True

    def __init__(
        self,
        username: str = "admin",
        password: str = "district",
        timeout: float = 30.0,
    ) -> None:
        """Initialize with credentials and timeout."""
        self.username = username
        self.password = password
        self.timeout = timeout

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check DHIS2 instance health via /api/system/info."""
        # Add https:// if no protocol specified
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        details: dict[str, object] = {}

        try:
            start = time.perf_counter()
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                auth=(self.username, self.password),
            ) as client:
                # First, follow redirects to get the actual base URL
                base_response = client.get(url)
                base_url = str(base_response.url).rstrip("/")

                # Remove any path after the base (like /dhis-web-login/, /login/, etc.)
                for path_suffix in ["/dhis-web-", "/login", "/#"]:
                    if path_suffix in base_url:
                        base_url = base_url.split(path_suffix)[0]
                        break

                # Now call the API endpoint
                api_url = f"{base_url}/api/system/info"
                response = client.get(api_url)
                elapsed_ms = (time.perf_counter() - start) * 1000

                details["status_code"] = response.status_code
                details["base_url"] = base_url
                details["api_url"] = api_url

                # Store response data in context for subsequent stages
                if context is not None:
                    context.response_body = response.text
                    context.response_headers = dict(response.headers)
                    context.status_code = response.status_code
                    context.elapsed_ms = elapsed_ms

                if response.status_code == 401:
                    return CheckResult(
                        status=Status.DOWN,
                        url=url,
                        message="Authentication failed",
                        elapsed_ms=elapsed_ms,
                        details=details,
                    )

                if response.status_code == 200:
                    # Parse DHIS2 system info
                    try:
                        info = response.json()
                        version = info.get("version", "unknown")
                        details["version"] = version
                        details["revision"] = info.get("revision", "unknown")
                        details["build_time"] = info.get("buildTime", "unknown")
                        details["server_date"] = info.get("serverDate", "unknown")
                        details["system_name"] = info.get("systemName", "unknown")

                        return CheckResult(
                            status=Status.UP,
                            url=url,
                            message=f"{version}",
                            elapsed_ms=elapsed_ms,
                            details=details,
                        )
                    except Exception:
                        return CheckResult(
                            status=Status.DEGRADED,
                            url=url,
                            message="Invalid JSON response",
                            elapsed_ms=elapsed_ms,
                            details=details,
                        )

                # Other status codes
                if response.status_code < 400:
                    return CheckResult(
                        status=Status.UP,
                        url=url,
                        message=str(response.status_code),
                        elapsed_ms=elapsed_ms,
                        details=details,
                    )
                else:
                    return CheckResult(
                        status=Status.DEGRADED,
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
