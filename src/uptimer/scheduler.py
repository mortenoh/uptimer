"""Background scheduler for running monitor checks."""

# APScheduler doesn't have type stubs, suppress unknown member type errors
# pyright: reportUnknownMemberType=false

import uuid
from datetime import datetime, timezone

import structlog
from apscheduler.jobstores.mongodb import MongoDBJobStore  # type: ignore[import-untyped]
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]

from uptimer.pipeline import run_pipeline
from uptimer.schemas import CheckResultRecord, Monitor
from uptimer.settings import get_settings
from uptimer.storage import Storage

logger = structlog.get_logger()

# Global scheduler instance
_scheduler: BackgroundScheduler | None = None


def run_monitor_check(monitor_id: str) -> None:
    """Run a check for a specific monitor.

    Args:
        monitor_id: ID of the monitor to check
    """
    # Import here to avoid circular import
    from uptimer.web.api.deps import get_storage

    storage = get_storage()
    monitor = storage.get_monitor(monitor_id)
    if not monitor:
        logger.warning("Monitor not found for scheduled check", monitor_id=monitor_id)
        return

    if not monitor.enabled:
        logger.debug("Skipping disabled monitor", monitor_id=monitor_id, name=monitor.name)
        return

    logger.info("Running scheduled check", monitor_id=monitor_id, name=monitor.name)

    try:
        final_status, message, total_elapsed_ms, all_details = run_pipeline(monitor.url, monitor.pipeline)
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
                args=[monitor.id],
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
            args=[monitor.id],
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
