#!/usr/bin/env python3
"""Seed MongoDB with sample monitor data for common websites."""

from uptimer.schemas import MonitorCreate
from uptimer.settings import get_settings
from uptimer.storage import Storage

# Common websites to monitor - all publicly accessible and introspectable
SEED_MONITORS = [
    MonitorCreate(
        name="Google",
        url="https://www.google.com",
        checker="http",
        interval=60,
        tags=["search", "google", "public"],
    ),
    MonitorCreate(
        name="GitHub",
        url="https://github.com",
        checker="http",
        interval=60,
        tags=["developer", "git", "public"],
    ),
    MonitorCreate(
        name="Cloudflare",
        url="https://www.cloudflare.com",
        checker="http",
        interval=60,
        tags=["infrastructure", "cdn", "public"],
    ),
    MonitorCreate(
        name="Amazon",
        url="https://www.amazon.com",
        checker="http",
        interval=60,
        tags=["ecommerce", "aws", "public"],
    ),
    MonitorCreate(
        name="Wikipedia",
        url="https://www.wikipedia.org",
        checker="http",
        interval=60,
        tags=["knowledge", "public"],
    ),
    MonitorCreate(
        name="Reddit",
        url="https://www.reddit.com",
        checker="http",
        interval=60,
        tags=["social", "public"],
    ),
    MonitorCreate(
        name="Stack Overflow",
        url="https://stackoverflow.com",
        checker="http",
        interval=60,
        tags=["developer", "public"],
    ),
    MonitorCreate(
        name="OpenAI",
        url="https://www.openai.com",
        checker="http",
        interval=60,
        tags=["ai", "public"],
    ),
    MonitorCreate(
        name="Anthropic",
        url="https://www.anthropic.com",
        checker="http",
        interval=60,
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
        interval=60,
        tags=["dhis2", "demo", "health"],
    ),
]


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
        print(f"Created: {monitor.name} [{tags_str}]")
        created += 1

    # Show all tags
    all_tags = storage.list_tags()
    print(f"\nSeeding complete: {created} created, {skipped} skipped")
    print(f"Available tags: {', '.join(all_tags)}")


if __name__ == "__main__":
    main()
