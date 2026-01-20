"""MongoDB storage for monitors and check results."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from uptimer.schemas import CheckResultRecord, Monitor, MonitorCreate, MonitorUpdate
from uptimer.validation import validate_checker, validate_interval, validate_url


class Storage:
    """MongoDB storage for monitors and results."""

    def __init__(
        self,
        mongodb_uri: str = "mongodb://localhost:27017",
        mongodb_db: str = "uptimer",
        results_retention: int = 1000,
        client: MongoClient[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize storage.

        Args:
            mongodb_uri: MongoDB connection URI
            mongodb_db: Database name
            results_retention: Max results to keep per monitor
            client: Optional MongoClient instance (for testing with mongomock)
        """
        self.results_retention = results_retention
        self._client: MongoClient[dict[str, Any]] = client or MongoClient(mongodb_uri)
        self._db: Database[dict[str, Any]] = self._client[mongodb_db]
        self._monitors: Collection[dict[str, Any]] = self._db["monitors"]
        self._results: Collection[dict[str, Any]] = self._db["results"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        self._results.create_index([("monitor_id", ASCENDING)])
        self._results.create_index([("monitor_id", ASCENDING), ("checked_at", DESCENDING)])
        self._monitors.create_index([("tags", ASCENDING)])

    # Monitor operations

    def list_monitors(self, tag: str | None = None) -> list[Monitor]:
        """List all monitors, optionally filtered by tag.

        Args:
            tag: Optional tag to filter by

        Returns:
            List of monitors
        """
        query: dict[str, Any] = {}
        if tag:
            query["tags"] = tag
        docs = self._monitors.find(query)
        return [Monitor(**self._doc_to_monitor(doc)) for doc in docs]

    def list_tags(self) -> list[str]:
        """List all unique tags across all monitors.

        Returns:
            Sorted list of unique tags
        """
        tags: list[str] = self._monitors.distinct("tags")
        return sorted(tags)

    def get_monitor(self, monitor_id: str) -> Monitor | None:
        """Get a monitor by ID."""
        doc = self._monitors.find_one({"_id": monitor_id})
        if doc:
            return Monitor(**self._doc_to_monitor(doc))
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
        monitor_id = str(uuid.uuid4())

        doc = {
            "_id": monitor_id,
            "name": data.name,
            "url": url,
            "checker": data.checker,
            "username": data.username,
            "password": data.password,
            "interval": data.interval,
            "schedule": data.schedule,
            "enabled": data.enabled,
            "tags": data.tags,
            "created_at": now,
            "updated_at": now,
            "last_check": None,
            "last_status": None,
        }

        self._monitors.insert_one(doc)

        return Monitor(**self._doc_to_monitor(doc))

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
        doc = self._monitors.find_one({"_id": monitor_id})
        if not doc:
            return None

        # Apply updates
        update_data = data.model_dump(exclude_unset=True)

        # Validate updated fields
        if "url" in update_data:
            update_data["url"] = validate_url(update_data["url"])
        if "checker" in update_data:
            validate_checker(update_data["checker"])
        if "interval" in update_data:
            validate_interval(update_data["interval"])

        update_data["updated_at"] = datetime.now(timezone.utc)

        self._monitors.update_one({"_id": monitor_id}, {"$set": update_data})

        updated_doc = self._monitors.find_one({"_id": monitor_id})
        if updated_doc:
            return Monitor(**self._doc_to_monitor(updated_doc))
        return None

    def delete_monitor(self, monitor_id: str) -> bool:
        """Delete a monitor.

        Args:
            monitor_id: ID of monitor to delete

        Returns:
            True if deleted, False if not found
        """
        result = self._monitors.delete_one({"_id": monitor_id})

        if result.deleted_count > 0:
            # Also delete associated results
            self._results.delete_many({"monitor_id": monitor_id})
            return True

        return False

    def update_monitor_status(self, monitor_id: str, status: str, checked_at: datetime) -> None:
        """Update monitor's last check status.

        Args:
            monitor_id: ID of monitor
            status: Check status
            checked_at: When check was performed
        """
        self._monitors.update_one(
            {"_id": monitor_id},
            {
                "$set": {
                    "last_status": status,
                    "last_check": checked_at,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    # Result operations

    def add_result(self, result: CheckResultRecord) -> None:
        """Add a check result.

        Args:
            result: Check result to add
        """
        doc = result.model_dump(mode="json")
        doc["_id"] = doc.pop("id")
        self._results.insert_one(doc)

        # Apply retention limit per monitor
        self._enforce_retention(result.monitor_id)

    def _enforce_retention(self, monitor_id: str) -> None:
        """Enforce results retention limit for a monitor.

        Args:
            monitor_id: ID of monitor to enforce retention for
        """
        count = self._results.count_documents({"monitor_id": monitor_id})
        if count > self.results_retention:
            # Find the oldest results to delete
            excess = count - self.results_retention
            oldest = (
                self._results.find({"monitor_id": monitor_id}, {"_id": 1}).sort("checked_at", ASCENDING).limit(excess)
            )

            ids_to_delete = [doc["_id"] for doc in oldest]
            if ids_to_delete:
                self._results.delete_many({"_id": {"$in": ids_to_delete}})

    def get_results(self, monitor_id: str, limit: int = 100) -> list[CheckResultRecord]:
        """Get check results for a monitor.

        Args:
            monitor_id: ID of monitor
            limit: Maximum results to return

        Returns:
            List of check results, most recent first
        """
        docs = self._results.find({"monitor_id": monitor_id}).sort("checked_at", DESCENDING).limit(limit)
        return [CheckResultRecord(**self._doc_to_result(doc)) for doc in docs]

    # Helper methods

    def _doc_to_monitor(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Convert MongoDB document to monitor dict.

        Args:
            doc: MongoDB document

        Returns:
            Dict suitable for Monitor model
        """
        result = dict(doc)
        result["id"] = result.pop("_id")
        return result

    def _doc_to_result(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Convert MongoDB document to result dict.

        Args:
            doc: MongoDB document

        Returns:
            Dict suitable for CheckResultRecord model
        """
        result = dict(doc)
        result["id"] = result.pop("_id")
        return result
