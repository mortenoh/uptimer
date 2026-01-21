"""MongoDB storage for monitors and check results."""

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from uptimer.schemas import (
    CheckResultRecord,
    Monitor,
    MonitorCreate,
    MonitorUpdate,
    Webhook,
    WebhookCreate,
    WebhookDelivery,
    WebhookUpdate,
)
from uptimer.validation import validate_interval, validate_stage, validate_url

logger = structlog.get_logger()


class Storage:
    """MongoDB storage for monitors and results."""

    def __init__(
        self,
        mongodb_uri: str = "mongodb://localhost:27017",
        mongodb_db: str = "uptimer",
        results_retention: int = 10_000_000,
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
        self._webhooks: Collection[dict[str, Any]] = self._db["webhooks"]
        self._webhook_deliveries: Collection[dict[str, Any]] = self._db["webhook_deliveries"]
        self._validate_connection()
        self._ensure_indexes()

    def _validate_connection(self) -> None:
        """Validate MongoDB connection is working."""
        try:
            # Ping the server to verify connection
            self._client.admin.command("ping")
            logger.debug("MongoDB connection validated")
        except ConnectionFailure as e:
            logger.error("MongoDB connection failed", error=str(e))
            raise ConnectionFailure(f"Failed to connect to MongoDB: {e}") from e

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        self._results.create_index([("monitor_id", ASCENDING)])
        self._results.create_index([("monitor_id", ASCENDING), ("checked_at", DESCENDING)])
        self._monitors.create_index([("tags", ASCENDING)])
        self._webhooks.create_index([("monitor_ids", ASCENDING)])
        self._webhooks.create_index([("tags", ASCENDING)])
        self._webhook_deliveries.create_index([("webhook_id", ASCENDING)])
        self._webhook_deliveries.create_index([("webhook_id", ASCENDING), ("attempted_at", DESCENDING)])

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
        tags: list[str | None] = self._monitors.distinct("tags")
        return sorted(t for t in tags if t is not None)

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
        for stage in data.pipeline:
            validate_stage(stage.type)
        validate_interval(data.interval)

        now = datetime.now(timezone.utc)
        monitor_id = str(uuid.uuid4())

        doc = {
            "_id": monitor_id,
            "name": data.name,
            "url": url,
            "pipeline": [s.model_dump(exclude_none=True) for s in data.pipeline],
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
        if "pipeline" in update_data:
            # Convert Stage objects to dicts and validate
            pipeline_list: list[dict[str, Any]] = []
            for stage in update_data["pipeline"]:
                validate_stage(stage["type"])
                pipeline_list.append(stage)
            update_data["pipeline"] = pipeline_list
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

    # Webhook operations

    def list_webhooks(self) -> list[Webhook]:
        """List all webhooks.

        Returns:
            List of webhooks
        """
        docs = self._webhooks.find()
        return [Webhook(**self._doc_to_webhook(doc)) for doc in docs]

    def get_webhook(self, webhook_id: str) -> Webhook | None:
        """Get a webhook by ID."""
        doc = self._webhooks.find_one({"_id": webhook_id})
        if doc:
            return Webhook(**self._doc_to_webhook(doc))
        return None

    def create_webhook(self, data: WebhookCreate) -> Webhook:
        """Create a new webhook.

        Args:
            data: Webhook creation data

        Returns:
            Created webhook
        """
        now = datetime.now(timezone.utc)
        webhook_id = str(uuid.uuid4())

        doc = {
            "_id": webhook_id,
            "name": data.name,
            "url": data.url,
            "enabled": data.enabled,
            "monitor_ids": data.monitor_ids,
            "tags": data.tags,
            "secret": data.secret,
            "headers": data.headers,
            "created_at": now,
            "updated_at": now,
            "last_triggered": None,
            "last_status": None,
        }

        self._webhooks.insert_one(doc)
        return Webhook(**self._doc_to_webhook(doc))

    def update_webhook(self, webhook_id: str, data: WebhookUpdate) -> Webhook | None:
        """Update a webhook.

        Args:
            webhook_id: ID of webhook to update
            data: Fields to update

        Returns:
            Updated webhook or None if not found
        """
        doc = self._webhooks.find_one({"_id": webhook_id})
        if not doc:
            return None

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)

        self._webhooks.update_one({"_id": webhook_id}, {"$set": update_data})

        updated_doc = self._webhooks.find_one({"_id": webhook_id})
        if updated_doc:
            return Webhook(**self._doc_to_webhook(updated_doc))
        return None

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook.

        Args:
            webhook_id: ID of webhook to delete

        Returns:
            True if deleted, False if not found
        """
        result = self._webhooks.delete_one({"_id": webhook_id})

        if result.deleted_count > 0:
            # Also delete associated deliveries
            self._webhook_deliveries.delete_many({"webhook_id": webhook_id})
            return True

        return False

    def get_webhooks_for_monitor(self, monitor: Monitor) -> list[Webhook]:
        """Get webhooks that should receive alerts for a monitor.

        A webhook matches if:
        - It's enabled AND
        - (monitor_ids is empty OR monitor.id is in monitor_ids) AND
        - (tags is empty OR any of monitor's tags match webhook tags)

        Args:
            monitor: The monitor to find webhooks for

        Returns:
            List of matching webhooks
        """
        webhooks: list[Webhook] = []
        for doc in self._webhooks.find({"enabled": True}):
            webhook = Webhook(**self._doc_to_webhook(doc))

            # Check monitor_ids filter
            if webhook.monitor_ids and monitor.id not in webhook.monitor_ids:
                continue

            # Check tags filter
            if webhook.tags:
                if not any(tag in monitor.tags for tag in webhook.tags):
                    continue

            webhooks.append(webhook)

        return webhooks

    def update_webhook_last_triggered(self, webhook_id: str, status: str, triggered_at: datetime) -> None:
        """Update webhook's last triggered timestamp and status.

        Args:
            webhook_id: ID of webhook
            status: Delivery status ("success" or "failed")
            triggered_at: When the webhook was triggered
        """
        self._webhooks.update_one(
            {"_id": webhook_id},
            {
                "$set": {
                    "last_triggered": triggered_at,
                    "last_status": status,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    def add_webhook_delivery(self, delivery: WebhookDelivery) -> None:
        """Add a webhook delivery record.

        Args:
            delivery: Delivery record to add
        """
        doc = delivery.model_dump(mode="json")
        doc["_id"] = doc.pop("id")
        self._webhook_deliveries.insert_one(doc)

    def get_webhook_deliveries(self, webhook_id: str, limit: int = 100) -> list[WebhookDelivery]:
        """Get delivery history for a webhook.

        Args:
            webhook_id: ID of webhook
            limit: Maximum deliveries to return

        Returns:
            List of deliveries, most recent first
        """
        docs = self._webhook_deliveries.find({"webhook_id": webhook_id}).sort("attempted_at", DESCENDING).limit(limit)
        return [WebhookDelivery(**self._doc_to_delivery(doc)) for doc in docs]

    def _doc_to_webhook(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Convert MongoDB document to webhook dict.

        Args:
            doc: MongoDB document

        Returns:
            Dict suitable for Webhook model
        """
        result = dict(doc)
        result["id"] = result.pop("_id")
        return result

    def _doc_to_delivery(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Convert MongoDB document to delivery dict.

        Args:
            doc: MongoDB document

        Returns:
            Dict suitable for WebhookDelivery model
        """
        result = dict(doc)
        result["id"] = result.pop("_id")
        return result
