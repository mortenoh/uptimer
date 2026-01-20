"""JSON file-based storage for monitors and check results."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uptimer.schemas import CheckResultRecord, Monitor, MonitorCreate, MonitorUpdate
from uptimer.validation import validate_checker, validate_interval, validate_url


class Storage:
    """JSON file-based storage for monitors and results."""

    def __init__(self, data_dir: Path, results_retention: int = 1000) -> None:
        """Initialize storage.

        Args:
            data_dir: Directory to store JSON files
            results_retention: Max results to keep per monitor
        """
        self.data_dir = data_dir
        self.results_retention = results_retention
        self.monitors_file = data_dir / "monitors.json"
        self.results_file = data_dir / "results.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load_monitors(self) -> list[dict[str, Any]]:
        """Load monitors from JSON file."""
        if not self.monitors_file.exists():
            return []
        with open(self.monitors_file) as f:
            data: list[dict[str, Any]] = json.load(f)
            return data

    def _save_monitors(self, monitors: list[dict[str, Any]]) -> None:
        """Save monitors to JSON file."""
        with open(self.monitors_file, "w") as f:
            json.dump(monitors, f, indent=2, default=str)

    def _load_results(self) -> list[dict[str, Any]]:
        """Load results from JSON file."""
        if not self.results_file.exists():
            return []
        with open(self.results_file) as f:
            data: list[dict[str, Any]] = json.load(f)
            return data

    def _save_results(self, results: list[dict[str, Any]]) -> None:
        """Save results to JSON file."""
        with open(self.results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

    # Monitor operations

    def list_monitors(self) -> list[Monitor]:
        """List all monitors."""
        data = self._load_monitors()
        return [Monitor(**m) for m in data]

    def get_monitor(self, monitor_id: str) -> Monitor | None:
        """Get a monitor by ID."""
        data = self._load_monitors()
        for m in data:
            if m["id"] == monitor_id:
                return Monitor(**m)
        return None

    def create_monitor(self, data: MonitorCreate) -> Monitor:
        """Create a new monitor.

        Args:
            data: Monitor creation data

        Returns:
            Created monitor

        Raises:
            ValueError: If validation fails
        """
        # Validate
        url = validate_url(data.url)
        validate_checker(data.checker)
        validate_interval(data.interval)

        now = datetime.now(timezone.utc)
        monitor = Monitor(
            id=str(uuid.uuid4()),
            name=data.name,
            url=url,
            checker=data.checker,
            username=data.username,
            password=data.password,
            interval=data.interval,
            enabled=data.enabled,
            created_at=now,
            updated_at=now,
        )

        monitors = self._load_monitors()
        monitors.append(monitor.model_dump(mode="json"))
        self._save_monitors(monitors)

        return monitor

    def update_monitor(self, monitor_id: str, data: MonitorUpdate) -> Monitor | None:
        """Update a monitor.

        Args:
            monitor_id: ID of monitor to update
            data: Fields to update

        Returns:
            Updated monitor or None if not found

        Raises:
            ValueError: If validation fails
        """
        monitors = self._load_monitors()

        for i, m in enumerate(monitors):
            if m["id"] == monitor_id:
                # Apply updates
                update_data = data.model_dump(exclude_unset=True)

                # Validate updated fields
                if "url" in update_data:
                    update_data["url"] = validate_url(update_data["url"])
                if "checker" in update_data:
                    validate_checker(update_data["checker"])
                if "interval" in update_data:
                    validate_interval(update_data["interval"])

                for key, value in update_data.items():
                    m[key] = value

                m["updated_at"] = datetime.now(timezone.utc).isoformat()
                monitors[i] = m
                self._save_monitors(monitors)
                return Monitor(**m)

        return None

    def delete_monitor(self, monitor_id: str) -> bool:
        """Delete a monitor.

        Args:
            monitor_id: ID of monitor to delete

        Returns:
            True if deleted, False if not found
        """
        monitors = self._load_monitors()
        initial_count = len(monitors)
        monitors = [m for m in monitors if m["id"] != monitor_id]

        if len(monitors) < initial_count:
            self._save_monitors(monitors)
            # Also delete associated results
            results = self._load_results()
            results = [r for r in results if r["monitor_id"] != monitor_id]
            self._save_results(results)
            return True

        return False

    def update_monitor_status(
        self, monitor_id: str, status: str, checked_at: datetime
    ) -> None:
        """Update monitor's last check status.

        Args:
            monitor_id: ID of monitor
            status: Check status
            checked_at: When check was performed
        """
        monitors = self._load_monitors()
        for m in monitors:
            if m["id"] == monitor_id:
                m["last_status"] = status
                m["last_check"] = checked_at.isoformat()
                m["updated_at"] = datetime.now(timezone.utc).isoformat()
                break
        self._save_monitors(monitors)

    # Result operations

    def add_result(self, result: CheckResultRecord) -> None:
        """Add a check result.

        Args:
            result: Check result to add
        """
        results = self._load_results()
        results.append(result.model_dump(mode="json"))

        # Apply retention limit per monitor
        monitor_results: dict[str, list[dict[str, Any]]] = {}
        for r in results:
            mid = r["monitor_id"]
            if mid not in monitor_results:
                monitor_results[mid] = []
            monitor_results[mid].append(r)

        # Keep only the most recent results per monitor
        trimmed: list[dict[str, Any]] = []
        for mid, mresults in monitor_results.items():
            # Sort by checked_at descending
            mresults.sort(key=lambda x: x["checked_at"], reverse=True)
            trimmed.extend(mresults[: self.results_retention])

        self._save_results(trimmed)

    def get_results(
        self, monitor_id: str, limit: int = 100
    ) -> list[CheckResultRecord]:
        """Get check results for a monitor.

        Args:
            monitor_id: ID of monitor
            limit: Maximum results to return

        Returns:
            List of check results, most recent first
        """
        results = self._load_results()
        monitor_results = [r for r in results if r["monitor_id"] == monitor_id]
        # Sort by checked_at descending
        monitor_results.sort(key=lambda x: x["checked_at"], reverse=True)
        return [CheckResultRecord(**r) for r in monitor_results[:limit]]
