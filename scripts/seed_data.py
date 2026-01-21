#!/usr/bin/env python3
"""Seed MongoDB with sample monitor data for common websites."""

import os
import uuid
from datetime import datetime, timezone

from uptimer.schemas import CheckResultRecord, MonitorCreate, Stage
from uptimer.settings import get_settings
from uptimer.stages import get_stage
from uptimer.storage import Storage

# Common websites to monitor - all publicly accessible and introspectable
SEED_MONITORS = [
    # Local test service - use for testing scheduler with up/down cycles
    MonitorCreate(
        name="Local Test Service",
        url="http://localhost:8081",
        pipeline=[Stage(type="http")],
        interval=10,
        tags=["local", "test"],
    ),
    MonitorCreate(
        name="Google",
        url="https://www.google.com",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["search", "google", "public"],
    ),
    MonitorCreate(
        name="GitHub",
        url="https://github.com",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["developer", "git", "public"],
    ),
    MonitorCreate(
        name="Cloudflare",
        url="https://www.cloudflare.com",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["infrastructure", "cdn", "public"],
    ),
    MonitorCreate(
        name="Amazon",
        url="https://www.amazon.com",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["ecommerce", "aws", "public"],
    ),
    MonitorCreate(
        name="Wikipedia",
        url="https://www.wikipedia.org",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["knowledge", "public"],
    ),
    MonitorCreate(
        name="Reddit",
        url="https://www.reddit.com",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["social", "public"],
    ),
    MonitorCreate(
        name="Stack Overflow",
        url="https://stackoverflow.com",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["developer", "public"],
    ),
    MonitorCreate(
        name="OpenAI",
        url="https://www.openai.com",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["ai", "public"],
    ),
    MonitorCreate(
        name="Anthropic",
        url="https://www.anthropic.com",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["ai", "public"],
    ),
    MonitorCreate(
        name="httpbin (test)",
        url="https://httpbin.org/get",
        pipeline=[Stage(type="http")],
        interval=30,
        tags=["test", "api", "public"],
    ),
    # DHIS2 instances with version/system info validation
    MonitorCreate(
        name="DHIS2 Demo",
        url="https://play.dhis2.org/demo",
        pipeline=[Stage(type="dhis2", username="admin", password="district")],
        interval=30,
        tags=["dhis2", "demo", "health"],
    ),
    MonitorCreate(
        name="DHIS2 Dev",
        url="https://play.dhis2.org/dev",
        pipeline=[Stage(type="dhis2", username="admin", password="district")],
        interval=30,
        tags=["dhis2", "dev", "health"],
    ),
]


def run_pipeline(storage: Storage, monitor_id: str, url: str, pipeline: list[Stage]) -> str:
    """Run all pipeline stages for a monitor and store the result."""
    all_details: dict[str, object] = {}
    total_elapsed_ms = 0.0
    final_status = "up"
    messages: list[str] = []

    for stage in pipeline:
        stage_class = get_stage(stage.type)

        # Instantiate stage with credentials if needed
        if stage.username and stage.password:
            try:
                stage_instance = stage_class(username=stage.username, password=stage.password)  # type: ignore[call-arg]
            except TypeError:
                stage_instance = stage_class()
        else:
            stage_instance = stage_class()

        result = stage_instance.check(url, verbose=False)
        total_elapsed_ms += result.elapsed_ms
        messages.append(f"{stage.type}: {result.message}")
        all_details[stage.type] = result.details

        # Use worst status (down > degraded > up)
        if result.status.value == "down":
            final_status = "down"
        elif result.status.value == "degraded" and final_status != "down":
            final_status = "degraded"

    now = datetime.now(timezone.utc)

    # Create and store result
    record = CheckResultRecord(
        id=str(uuid.uuid4()),
        monitor_id=monitor_id,
        status=final_status,
        message="; ".join(messages),
        elapsed_ms=total_elapsed_ms,
        details=all_details,
        checked_at=now,
    )
    storage.add_result(record)
    storage.update_monitor_status(monitor_id, final_status, now)

    return final_status


def main() -> None:
    """Seed the database with sample monitors."""
    settings = get_settings()
    storage = Storage(
        mongodb_uri=settings.mongodb_uri,
        mongodb_db=settings.mongodb_db,
        results_retention=settings.results_retention,
    )

    # Check existing monitors
    existing = storage.list_monitors()
    existing_urls = {m.url for m in existing}

    # Limit number of monitors with N env var
    n = int(os.environ.get("N", 0))
    monitors_to_seed = SEED_MONITORS[:n] if n > 0 else SEED_MONITORS

    created = 0
    skipped = 0

    for monitor_data in monitors_to_seed:
        if monitor_data.url in existing_urls:
            print(f"Skipping {monitor_data.name} - already exists")
            skipped += 1
            continue

        monitor = storage.create_monitor(monitor_data)
        tags_str = ", ".join(monitor.tags) if monitor.tags else "none"
        print(f"Created: {monitor.name} [{tags_str}]", end=" ... ")

        # Run initial pipeline
        try:
            status = run_pipeline(
                storage,
                monitor.id,
                monitor.url,
                monitor.pipeline,
            )
            print(f"[{status}]")
        except Exception as e:
            print(f"[check failed: {e}]")

        created += 1

    # Show all tags
    all_tags = storage.list_tags()
    print(f"\nSeeding complete: {created} created, {skipped} skipped")
    print(f"Available tags: {', '.join(all_tags)}")


if __name__ == "__main__":
    main()
