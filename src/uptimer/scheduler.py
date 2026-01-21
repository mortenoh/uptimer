"""Background scheduler for running monitor checks."""

# pyright: reportUnknownMemberType=false

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from apscheduler.jobstores.mongodb import MongoDBJobStore  # type: ignore[import-untyped]
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]

from uptimer.schemas import CheckResultRecord, Monitor, Stage
from uptimer.settings import get_settings
from uptimer.stages import CheckContext, get_stage
from uptimer.storage import Storage

logger = structlog.get_logger()

# Global scheduler instance
_scheduler: BackgroundScheduler | None = None


def _instantiate_stage(stage: Stage) -> Any:
    """Instantiate a stage with the appropriate options from Stage config."""
    stage_class = get_stage(stage.type)

    kwargs: dict[str, Any] = {}

    if stage.username:
        kwargs["username"] = stage.username
    if stage.password:
        kwargs["password"] = stage.password
    if stage.expr:
        kwargs["expr"] = stage.expr
    if stage.store_as:
        kwargs["store_as"] = stage.store_as
    if stage.min is not None:
        kwargs["min_value"] = stage.min
    if stage.max is not None:
        kwargs["max_value"] = stage.max
    if stage.value:
        kwargs["value_ref"] = stage.value
    if stage.pattern:
        kwargs["pattern"] = stage.pattern
    if stage.negate:
        kwargs["negate"] = stage.negate
    if stage.max_age is not None:
        kwargs["max_age"] = stage.max_age
    if stage.warn_days:
        kwargs["warn_days"] = stage.warn_days
    if stage.port is not None:
        kwargs["port"] = stage.port
    if stage.expected_ip:
        kwargs["expected_ip"] = stage.expected_ip
    if stage.schema_:
        kwargs["schema"] = stage.schema_
    if stage.headers:
        kwargs["headers"] = stage.headers

    try:
        return stage_class(**kwargs)
    except TypeError:
        return stage_class()


def _run_pipeline(url: str, pipeline: list[Stage]) -> tuple[str, str, float, dict[str, object]]:
    """Run all pipeline stages for a monitor and return aggregated results."""
    context = CheckContext(url=url)

    all_details: dict[str, object] = {}
    total_elapsed_ms = 0.0
    final_status = "up"
    messages: list[str] = []

    for i, stage in enumerate(pipeline):
        checker = _instantiate_stage(stage)
        result = checker.check(url, verbose=False, context=context)

        total_elapsed_ms += result.elapsed_ms
        messages.append(f"{stage.type}: {result.message}")

        stage_key = f"{stage.type}" if pipeline.count(stage) == 1 else f"{stage.type}_{i}"
        all_details[stage_key] = result.details

        if result.status.value == "down":
            final_status = "down"
        elif result.status.value == "degraded" and final_status != "down":
            final_status = "degraded"

    if context.values:
        all_details["_values"] = context.values

    return final_status, "; ".join(messages), total_elapsed_ms, all_details


def run_monitor_check(monitor_id: str, storage: Storage) -> None:
    """Run a check for a specific monitor.

    Args:
        monitor_id: ID of the monitor to check
        storage: Storage instance
    """
    monitor = storage.get_monitor(monitor_id)
    if not monitor:
        logger.warning("Monitor not found for scheduled check", monitor_id=monitor_id)
        return

    if not monitor.enabled:
        logger.debug("Skipping disabled monitor", monitor_id=monitor_id, name=monitor.name)
        return

    logger.info("Running scheduled check", monitor_id=monitor_id, name=monitor.name)

    try:
        final_status, message, total_elapsed_ms, all_details = _run_pipeline(monitor.url, monitor.pipeline)
        now = datetime.now(timezone.utc)

        record = CheckResultRecord(
            id=str(uuid.uuid4()),
            monitor_id=monitor_id,
            status=final_status,
            message=message,
            elapsed_ms=total_elapsed_ms,
            details=all_details,
            checked_at=now,
        )

        storage.add_result(record)
        storage.update_monitor_status(monitor_id, final_status, now)

        logger.info(
            "Scheduled check completed",
            monitor_id=monitor_id,
            name=monitor.name,
            status=final_status,
            elapsed_ms=round(total_elapsed_ms, 1),
        )
    except Exception as e:
        logger.error("Scheduled check failed", monitor_id=monitor_id, name=monitor.name, error=str(e))


def _add_monitor_job(scheduler: BackgroundScheduler, monitor: Monitor, storage: Storage) -> None:
    """Add a job for a monitor to the scheduler.

    Args:
        scheduler: The APScheduler instance
        monitor: The monitor to schedule
        storage: Storage instance for running checks
    """
    job_id = f"monitor_{monitor.id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if not monitor.enabled:
        logger.debug("Not scheduling disabled monitor", monitor_id=monitor.id, name=monitor.name)
        return

    if monitor.schedule:
        # Cron-based schedule
        try:
            trigger = CronTrigger.from_crontab(monitor.schedule)
            scheduler.add_job(
                run_monitor_check,
                trigger=trigger,
                args=[monitor.id, storage],
                id=job_id,
                name=f"Check: {monitor.name}",
                replace_existing=True,
            )
            logger.info("Scheduled monitor (cron)", monitor_id=monitor.id, name=monitor.name, schedule=monitor.schedule)
        except ValueError as e:
            logger.error("Invalid cron expression", monitor_id=monitor.id, schedule=monitor.schedule, error=str(e))
    else:
        # Interval-based schedule
        trigger = IntervalTrigger(seconds=monitor.interval)
        scheduler.add_job(
            run_monitor_check,
            trigger=trigger,
            args=[monitor.id, storage],
            id=job_id,
            name=f"Check: {monitor.name}",
            replace_existing=True,
        )
        logger.info("Scheduled monitor (interval)", monitor_id=monitor.id, name=monitor.name, interval=monitor.interval)


def start_scheduler(storage: Storage) -> BackgroundScheduler:
    """Start the background scheduler and schedule all monitors.

    Args:
        storage: Storage instance for accessing monitors

    Returns:
        The running scheduler instance
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler already running")
        return _scheduler

    # Configure MongoDB job store
    settings = get_settings()
    jobstores = {
        "default": MongoDBJobStore(
            database=settings.mongodb_db,
            collection="scheduler_jobs",
            host=settings.mongodb_uri,
        )
    }

    _scheduler = BackgroundScheduler(jobstores=jobstores)

    # Schedule all enabled monitors
    monitors = storage.list_monitors()
    for monitor in monitors:
        _add_monitor_job(_scheduler, monitor, storage)

    _scheduler.start()
    logger.info("Scheduler started", monitor_count=len(monitors), jobstore="mongodb")

    return _scheduler


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
        _scheduler = None


def get_scheduler() -> BackgroundScheduler | None:
    """Get the current scheduler instance."""
    return _scheduler


def refresh_monitor_schedule(monitor: Monitor, storage: Storage) -> None:
    """Refresh the schedule for a specific monitor.

    Call this when a monitor is created or updated.

    Args:
        monitor: The monitor to refresh
        storage: Storage instance
    """
    if _scheduler is None or not _scheduler.running:
        return

    _add_monitor_job(_scheduler, monitor, storage)


def remove_monitor_schedule(monitor_id: str) -> None:
    """Remove a monitor from the schedule.

    Call this when a monitor is deleted.

    Args:
        monitor_id: ID of the monitor to remove
    """
    if _scheduler is None or not _scheduler.running:
        return

    job_id = f"monitor_{monitor_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
        logger.info("Removed monitor from schedule", monitor_id=monitor_id)
