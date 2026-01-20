#!/usr/bin/env python3
"""Seed MongoDB with sample monitor data for common websites."""

import uuid
from datetime import datetime, timezone

from uptimer.checkers import get_checker
from uptimer.schemas import CheckResultRecord, MonitorCreate
from uptimer.settings import get_settings
from uptimer.storage import Storage

# Common websites to monitor - all publicly accessible and introspectable
SEED_MONITORS = [
    MonitorCreate(
        name="Google",
        url="https://www.google.com",
        checker="http",
        interval=30,
        tags=["search", "google", "public"],
    ),
    MonitorCreate(
        name="GitHub",
        url="https://github.com",
        checker="http",
        interval=30,
        tags=["developer", "git", "public"],
    ),
    MonitorCreate(
        name="Cloudflare",
        url="https://www.cloudflare.com",
        checker="http",
        interval=30,
        tags=["infrastructure", "cdn", "public"],
    ),
    MonitorCreate(
        name="Amazon",
        url="https://www.amazon.com",
        checker="http",
        interval=30,
        tags=["ecommerce", "aws", "public"],
    ),
    MonitorCreate(
        name="Wikipedia",
        url="https://www.wikipedia.org",
        checker="http",
        interval=30,
        tags=["knowledge", "public"],
    ),
    MonitorCreate(
        name="Reddit",
        url="https://www.reddit.com",
        checker="http",
        interval=30,
        tags=["social", "public"],
    ),
    MonitorCreate(
        name="Stack Overflow",
        url="https://stackoverflow.com",
        checker="http",
        interval=30,
        tags=["developer", "public"],
    ),
    MonitorCreate(
        name="OpenAI",
        url="https://www.openai.com",
        checker="http",
        interval=30,
        tags=["ai", "public"],
    ),
    MonitorCreate(
        name="Anthropic",
        url="https://www.anthropic.com",
        checker="http",
        interval=30,
        tags=["ai", "public"],
    ),
    MonitorCreate(
        name="httpbin (test)",
        url="https://httpbin.org/get",
        checker="http",
        interval=30,
        tags=["test", "api", "public"],
    ),
    # DHIS2 instance with version/system info validation
    MonitorCreate(
        name="DHIS2 Demo",
        url="https://play.dhis2.org/demo",
        checker="dhis2",
        username="admin",
        password="district",
        interval=30,
        tags=["dhis2", "demo", "health"],
    ),
]


def run_check(storage: Storage, monitor_id: str, url: str, checker_name: str,
              username: str | None = None, password: str | None = None) -> str:
    """Run a check for a monitor and store the result."""
    checker_class = get_checker(checker_name)

    # Instantiate checker with credentials if needed
    if username and password:
        try:
            checker = checker_class(username=username, password=password)
        except TypeError:
            checker = checker_class()
    else:
        checker = checker_class()

    result = checker.check(url, verbose=False)
    now = datetime.now(timezone.utc)

    # Create and store result
    record = CheckResultRecord(
        id=str(uuid.uuid4()),
        monitor_id=monitor_id,
        status=result.status.value,
        message=result.message,
        elapsed_ms=result.elapsed_ms,
        details=result.details,
        checked_at=now,
    )
    storage.add_result(record)
    storage.update_monitor_status(monitor_id, result.status.value, now)

    return result.status.value


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

    created = 0
    skipped = 0

    for monitor_data in SEED_MONITORS:
        if monitor_data.url in existing_urls:
            print(f"Skipping {monitor_data.name} - already exists")
            skipped += 1
            continue

        monitor = storage.create_monitor(monitor_data)
        tags_str = ", ".join(monitor.tags) if monitor.tags else "none"
        print(f"Created: {monitor.name} [{tags_str}]", end=" ... ")

        # Run initial check
        try:
            status = run_check(
                storage,
                monitor.id,
                monitor.url,
                monitor.checker,
                monitor_data.username,
                monitor_data.password,
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
