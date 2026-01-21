"""API client for uptimer backend."""

from typing import Any

import httpx

from uptimer.schemas import CheckResultRecord, Monitor, MonitorCreate


class UptimerClientError(Exception):
    """Base exception for client errors."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize the exception.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
        """
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(UptimerClientError):
    """Authentication failed."""


class NotFoundError(UptimerClientError):
    """Resource not found."""


class UptimerClient:
    """HTTP client for the uptimer API."""

    def __init__(self, base_url: str, username: str, password: str, timeout: float = 30.0):
        """Initialize the client.

        Args:
            base_url: Base URL of the API (e.g., http://localhost:8000)
            username: Username for Basic Auth
            password: Password for Basic Auth
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an HTTP request to the API.

        Args:
            method: HTTP method
            path: API path (will be joined with base_url)
            json: JSON body data
            params: Query parameters

        Returns:
            HTTP response

        Raises:
            AuthenticationError: If authentication fails
            NotFoundError: If resource not found
            UptimerClientError: For other errors
        """
        url = f"{self.base_url}{path}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method,
                    url,
                    auth=self.auth,
                    json=json,
                    params=params,
                )
        except httpx.ConnectError as e:
            raise UptimerClientError(f"Failed to connect to {self.base_url}: {e}") from e
        except httpx.TimeoutException as e:
            raise UptimerClientError(f"Request timed out: {e}") from e

        if response.status_code == 401:
            raise AuthenticationError("Authentication failed", status_code=401)
        if response.status_code == 404:
            raise NotFoundError("Resource not found", status_code=404)
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise UptimerClientError(f"API error: {detail}", status_code=response.status_code)

        return response

    def list_monitors(self, tag: str | None = None) -> list[Monitor]:
        """List all monitors, optionally filtered by tag.

        Args:
            tag: Optional tag to filter by

        Returns:
            List of monitors
        """
        params: dict[str, Any] | None = {"tag": tag} if tag else None
        response = self._request("GET", "/api/monitors", params=params)
        return [Monitor.model_validate(m) for m in response.json()]

    def get_monitor(self, monitor_id: str) -> Monitor:
        """Get a monitor by ID.

        Args:
            monitor_id: Monitor ID

        Returns:
            Monitor

        Raises:
            NotFoundError: If monitor not found
        """
        response = self._request("GET", f"/api/monitors/{monitor_id}")
        return Monitor.model_validate(response.json())

    def create_monitor(self, data: MonitorCreate) -> Monitor:
        """Create a new monitor.

        Args:
            data: Monitor creation data

        Returns:
            Created monitor
        """
        response = self._request("POST", "/api/monitors", json=data.model_dump())
        return Monitor.model_validate(response.json())

    def delete_monitor(self, monitor_id: str) -> None:
        """Delete a monitor.

        Args:
            monitor_id: Monitor ID

        Raises:
            NotFoundError: If monitor not found
        """
        self._request("DELETE", f"/api/monitors/{monitor_id}")

    def run_check(self, monitor_id: str) -> CheckResultRecord:
        """Run a check for a monitor.

        Args:
            monitor_id: Monitor ID

        Returns:
            Check result

        Raises:
            NotFoundError: If monitor not found
        """
        response = self._request("POST", f"/api/monitors/{monitor_id}/check")
        return CheckResultRecord.model_validate(response.json())

    def run_all_checks(self, tag: str | None = None) -> list[CheckResultRecord]:
        """Run checks for all monitors.

        Args:
            tag: Optional tag to filter monitors

        Returns:
            List of check results
        """
        params: dict[str, Any] | None = {"tag": tag} if tag else None
        response = self._request("POST", "/api/monitors/check-all", params=params)
        return [CheckResultRecord.model_validate(r) for r in response.json()]

    def get_results(self, monitor_id: str, limit: int = 100) -> list[CheckResultRecord]:
        """Get check results for a monitor.

        Args:
            monitor_id: Monitor ID
            limit: Maximum number of results to return

        Returns:
            List of check results

        Raises:
            NotFoundError: If monitor not found
        """
        response = self._request("GET", f"/api/monitors/{monitor_id}/results", params={"limit": limit})
        return [CheckResultRecord.model_validate(r) for r in response.json()]

    def list_tags(self) -> list[str]:
        """List all unique tags.

        Returns:
            List of tags
        """
        response = self._request("GET", "/api/monitors/tags")
        tags: list[str] = response.json()
        return tags
