"""DHIS2-specific stages for version, integrity, and system checks."""

import re
import time
from typing import Any

import httpx

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


def _get_dhis2_base_url(url: str, client: httpx.Client) -> str:
    """Resolve DHIS2 base URL following redirects."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    response = client.get(url)
    base_url = str(response.url).rstrip("/")

    # Remove any path after the base (like /dhis-web-login/)
    if "/dhis-web-" in base_url:
        base_url = base_url.split("/dhis-web-")[0]

    return base_url


def _parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse DHIS2 version string into tuple.

    Args:
        version_str: Version like "2.40.1", "2.40", "40.1.0"

    Returns:
        Tuple of (major, minor, patch)
    """
    # Handle various formats
    match = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3)) if match.group(3) else 0

        # Normalize: "40.1.0" -> "2.40.1" (assume DHIS2.x)
        if major >= 30:  # It's actually the minor version
            return (2, major, minor)
        return (major, minor, patch)

    return (0, 0, 0)


def _compare_versions(v1: tuple[int, int, int], v2: tuple[int, int, int]) -> int:
    """Compare two version tuples.

    Returns:
        -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    for a, b in zip(v1, v2):
        if a < b:
            return -1
        if a > b:
            return 1
    return 0


@register_stage
class Dhis2VersionStage(Stage):
    """Check DHIS2 version meets minimum requirement."""

    name = "dhis2-version"
    description = "Check DHIS2 version meets minimum requirement"
    is_network_stage = True

    def __init__(
        self,
        username: str = "admin",
        password: str = "district",
        min_version: str = "2.38.0",
        timeout: float = 30.0,
    ) -> None:
        """Initialize version stage.

        Args:
            username: DHIS2 username
            password: DHIS2 password
            min_version: Minimum required version (e.g., "2.40.0")
            timeout: Request timeout
        """
        self.username = username
        self.password = password
        self.min_version = min_version
        self.min_version_tuple = _parse_version(min_version)
        self.timeout = timeout

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check if DHIS2 version meets minimum requirement."""
        try:
            start = time.perf_counter()
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                auth=(self.username, self.password),
            ) as client:
                base_url = _get_dhis2_base_url(url, client)
                response = client.get(f"{base_url}/api/system/info")
                elapsed_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 401:
                    return CheckResult(
                        status=Status.DOWN,
                        url=url,
                        message="Authentication failed",
                        elapsed_ms=elapsed_ms,
                        details={"error": "401 Unauthorized"},
                    )

                info = response.json()
                version = info.get("version", "unknown")
                version_tuple = _parse_version(version)

                details: dict[str, Any] = {
                    "version": version,
                    "version_parsed": f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}",
                    "min_version": self.min_version,
                    "revision": info.get("revision", ""),
                    "build_time": info.get("buildTime", ""),
                }

                cmp = _compare_versions(version_tuple, self.min_version_tuple)

                if cmp < 0:
                    return CheckResult(
                        status=Status.DOWN,
                        url=url,
                        message=f"Version {version} < {self.min_version}",
                        elapsed_ms=elapsed_ms,
                        details=details,
                    )

                return CheckResult(
                    status=Status.UP,
                    url=url,
                    message=f"Version {version} >= {self.min_version}",
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


@register_stage
class Dhis2IntegrityStage(Stage):
    """Run DHIS2 data integrity checks."""

    name = "dhis2-integrity"
    description = "Run DHIS2 data integrity checks"
    is_network_stage = True

    def __init__(
        self,
        username: str = "admin",
        password: str = "district",
        timeout: float = 60.0,
    ) -> None:
        """Initialize integrity stage.

        Args:
            username: DHIS2 username
            password: DHIS2 password
            timeout: Request timeout (longer for integrity checks)
        """
        self.username = username
        self.password = password
        self.timeout = timeout

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Run DHIS2 data integrity checks."""
        try:
            start = time.perf_counter()
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                auth=(self.username, self.password),
            ) as client:
                base_url = _get_dhis2_base_url(url, client)

                # Get summary of data integrity
                response = client.get(f"{base_url}/api/dataIntegrity")
                elapsed_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 401:
                    return CheckResult(
                        status=Status.DOWN,
                        url=url,
                        message="Authentication failed",
                        elapsed_ms=elapsed_ms,
                        details={"error": "401 Unauthorized"},
                    )

                if response.status_code != 200:
                    return CheckResult(
                        status=Status.DEGRADED,
                        url=url,
                        message=f"Integrity check returned {response.status_code}",
                        elapsed_ms=elapsed_ms,
                        details={"status_code": response.status_code},
                    )

                checks: Any = response.json()

                # Count available checks
                checks_list: list[Any] = checks if isinstance(checks, list) else []  # pyright: ignore[reportUnknownVariableType]
                check_count = len(checks_list)

                return CheckResult(
                    status=Status.UP,
                    url=url,
                    message=f"{check_count} integrity checks available",
                    elapsed_ms=elapsed_ms,
                    details={
                        "check_count": check_count,
                        "checks": checks[:10] if isinstance(checks, list) else checks,
                    },
                )

        except httpx.RequestError as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=e.__class__.__name__,
                details={"error": str(e)},
            )


@register_stage
class Dhis2JobStage(Stage):
    """Check DHIS2 scheduled job status."""

    name = "dhis2-job"
    description = "Check DHIS2 scheduled job status"
    is_network_stage = True

    def __init__(
        self,
        username: str = "admin",
        password: str = "district",
        job_type: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize job stage.

        Args:
            username: DHIS2 username
            password: DHIS2 password
            job_type: Specific job type to check (e.g., "ANALYTICS_TABLE")
            timeout: Request timeout
        """
        self.username = username
        self.password = password
        self.job_type = job_type
        self.timeout = timeout

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check DHIS2 scheduled job status."""
        try:
            start = time.perf_counter()
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                auth=(self.username, self.password),
            ) as client:
                base_url = _get_dhis2_base_url(url, client)

                # Get job configurations
                endpoint = f"{base_url}/api/jobConfigurations"
                if self.job_type:
                    endpoint += f"?filter=jobType:eq:{self.job_type}"

                response = client.get(endpoint)
                elapsed_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 401:
                    return CheckResult(
                        status=Status.DOWN,
                        url=url,
                        message="Authentication failed",
                        elapsed_ms=elapsed_ms,
                        details={"error": "401 Unauthorized"},
                    )

                data = response.json()
                jobs = data.get("jobConfigurations", [])

                # Analyze job statuses
                enabled_count = sum(1 for j in jobs if j.get("enabled"))
                running_count = sum(1 for j in jobs if j.get("lastExecutedStatus") == "RUNNING")
                failed_count = sum(1 for j in jobs if j.get("lastExecutedStatus") == "FAILED")

                details: dict[str, Any] = {
                    "total_jobs": len(jobs),
                    "enabled": enabled_count,
                    "running": running_count,
                    "failed": failed_count,
                    "job_type_filter": self.job_type,
                }

                if failed_count > 0:
                    return CheckResult(
                        status=Status.DEGRADED,
                        url=url,
                        message=f"{failed_count} jobs failed",
                        elapsed_ms=elapsed_ms,
                        details=details,
                    )

                return CheckResult(
                    status=Status.UP,
                    url=url,
                    message=f"{len(jobs)} jobs ({enabled_count} enabled)",
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


@register_stage
class Dhis2AnalyticsStage(Stage):
    """Check DHIS2 analytics table status."""

    name = "dhis2-analytics"
    description = "Check DHIS2 analytics table generation status"
    is_network_stage = True

    def __init__(
        self,
        username: str = "admin",
        password: str = "district",
        max_age_hours: int = 24,
        timeout: float = 30.0,
    ) -> None:
        """Initialize analytics stage.

        Args:
            username: DHIS2 username
            password: DHIS2 password
            max_age_hours: Max hours since last analytics run
            timeout: Request timeout
        """
        self.username = username
        self.password = password
        self.max_age_hours = max_age_hours
        self.timeout = timeout

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Check DHIS2 analytics table status."""
        try:
            start = time.perf_counter()
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                auth=(self.username, self.password),
            ) as client:
                base_url = _get_dhis2_base_url(url, client)

                # Check system info for analytics status
                response = client.get(f"{base_url}/api/system/info")
                elapsed_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 401:
                    return CheckResult(
                        status=Status.DOWN,
                        url=url,
                        message="Authentication failed",
                        elapsed_ms=elapsed_ms,
                        details={"error": "401 Unauthorized"},
                    )

                info = response.json()

                # Get last analytics table generation time
                last_analytics = info.get("lastAnalyticsTableSuccess")
                last_analytics_runtime = info.get("lastAnalyticsTableRuntime")

                details: dict[str, Any] = {
                    "last_analytics_success": last_analytics,
                    "last_analytics_runtime": last_analytics_runtime,
                    "max_age_hours": self.max_age_hours,
                }

                if not last_analytics:
                    return CheckResult(
                        status=Status.DEGRADED,
                        url=url,
                        message="No analytics table generation recorded",
                        elapsed_ms=elapsed_ms,
                        details=details,
                    )

                # Parse the timestamp and check age
                from datetime import datetime, timezone

                try:
                    # DHIS2 returns ISO format
                    if last_analytics.endswith("Z"):
                        last_dt = datetime.fromisoformat(last_analytics.replace("Z", "+00:00"))
                    else:
                        last_dt = datetime.fromisoformat(last_analytics)
                        if last_dt.tzinfo is None:
                            last_dt = last_dt.replace(tzinfo=timezone.utc)

                    now = datetime.now(timezone.utc)
                    age_hours = (now - last_dt).total_seconds() / 3600
                    details["age_hours"] = round(age_hours, 1)

                    if age_hours > self.max_age_hours:
                        return CheckResult(
                            status=Status.DEGRADED,
                            url=url,
                            message=f"Analytics {age_hours:.1f}h old (max: {self.max_age_hours}h)",
                            elapsed_ms=elapsed_ms,
                            details=details,
                        )

                    return CheckResult(
                        status=Status.UP,
                        url=url,
                        message=f"Analytics {age_hours:.1f}h old",
                        elapsed_ms=elapsed_ms,
                        details=details,
                    )

                except (ValueError, TypeError):
                    return CheckResult(
                        status=Status.DEGRADED,
                        url=url,
                        message=f"Could not parse analytics timestamp: {last_analytics}",
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
