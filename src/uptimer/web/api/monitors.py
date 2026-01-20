"""Monitor API routes."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from uptimer.checkers import CheckContext, get_checker
from uptimer.schemas import CheckConfig, CheckResultRecord, Monitor, MonitorCreate, MonitorUpdate
from uptimer.storage import Storage
from uptimer.web.api.deps import get_storage, require_auth

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


def _instantiate_checker(check: CheckConfig) -> Any:
    """Instantiate a checker with the appropriate options from CheckConfig."""
    checker_class = get_checker(check.type)

    # Build kwargs from CheckConfig options
    kwargs: dict[str, Any] = {}

    # Auth options (for dhis2, etc.)
    if check.username:
        kwargs["username"] = check.username
    if check.password:
        kwargs["password"] = check.password

    # Value extractor options
    if check.expr:
        kwargs["expr"] = check.expr
    if check.store_as:
        kwargs["store_as"] = check.store_as

    # Threshold options
    if check.min is not None:
        kwargs["min_value"] = check.min
    if check.max is not None:
        kwargs["max_value"] = check.max
    if check.value:
        kwargs["value_ref"] = check.value

    # Pattern/contains options
    if check.pattern:
        kwargs["pattern"] = check.pattern
    if check.negate:
        kwargs["negate"] = check.negate

    # Age checker options
    if check.max_age is not None:
        kwargs["max_age"] = check.max_age

    # SSL options
    if check.warn_days:
        kwargs["warn_days"] = check.warn_days

    # TCP options
    if check.port is not None:
        kwargs["port"] = check.port

    # DNS options
    if check.expected_ip:
        kwargs["expected_ip"] = check.expected_ip

    # JSON schema options
    if check.schema_:
        kwargs["schema"] = check.schema_

    # Try to instantiate with kwargs, fall back to no-args
    try:
        return checker_class(**kwargs)
    except TypeError:
        return checker_class()


def _run_checks(url: str, checks: list[CheckConfig]) -> tuple[str, str, float, dict[str, object]]:
    """Run all checks for a monitor and return aggregated results.

    Args:
        url: URL to check
        checks: List of check configurations

    Returns:
        Tuple of (final_status, message, total_elapsed_ms, all_details)
    """
    # Create shared context for the check chain
    context = CheckContext(url=url)

    all_details: dict[str, object] = {}
    total_elapsed_ms = 0.0
    final_status = "up"
    messages: list[str] = []

    for i, check in enumerate(checks):
        checker = _instantiate_checker(check)
        result = checker.check(url, verbose=False, context=context)

        total_elapsed_ms += result.elapsed_ms
        messages.append(f"{check.type}: {result.message}")

        # Store check details with index to handle multiple checks of same type
        check_key = f"{check.type}" if checks.count(check) == 1 else f"{check.type}_{i}"
        all_details[check_key] = result.details

        # Use worst status (down > degraded > up)
        if result.status.value == "down":
            final_status = "down"
        elif result.status.value == "degraded" and final_status != "down":
            final_status = "degraded"

    # Include extracted values in details
    if context.values:
        all_details["_values"] = context.values

    return final_status, "; ".join(messages), total_elapsed_ms, all_details


@router.get("", response_model=list[Monitor])
async def list_monitors(
    tag: str | None = Query(default=None, description="Filter by tag"),
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> list[Monitor]:
    """List all monitors, optionally filtered by tag."""
    return storage.list_monitors(tag=tag)


@router.get("/tags", response_model=list[str])
async def list_tags(
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> list[str]:
    """List all unique tags."""
    return storage.list_tags()


@router.post("/check-all", response_model=list[CheckResultRecord])
async def check_all_monitors(
    tag: str | None = Query(default=None, description="Only check monitors with this tag"),
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> list[CheckResultRecord]:
    """Run checks for all monitors (optionally filtered by tag)."""
    monitors = storage.list_monitors(tag=tag)
    results: list[CheckResultRecord] = []

    for monitor in monitors:
        if not monitor.enabled:
            continue

        final_status, message, total_elapsed_ms, all_details = _run_checks(monitor.url, monitor.checks)
        now = datetime.now(timezone.utc)

        record = CheckResultRecord(
            id=str(uuid.uuid4()),
            monitor_id=monitor.id,
            status=final_status,
            message=message,
            elapsed_ms=total_elapsed_ms,
            details=all_details,
            checked_at=now,
        )

        storage.add_result(record)
        storage.update_monitor_status(monitor.id, final_status, now)
        results.append(record)

    return results


@router.post("", response_model=Monitor, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    data: MonitorCreate,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> Monitor:
    """Create a new monitor."""
    try:
        return storage.create_monitor(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from e


@router.get("/{monitor_id}", response_model=Monitor)
async def get_monitor(
    monitor_id: str,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> Monitor:
    """Get a monitor by ID."""
    monitor = storage.get_monitor(monitor_id)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )
    return monitor


@router.put("/{monitor_id}", response_model=Monitor)
async def update_monitor(
    monitor_id: str,
    data: MonitorUpdate,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> Monitor:
    """Update a monitor."""
    try:
        monitor = storage.update_monitor(monitor_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from e

    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    monitor_id: str,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> None:
    """Delete a monitor."""
    deleted = storage.delete_monitor(monitor_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )


@router.post("/{monitor_id}/check", response_model=CheckResultRecord)
async def run_check(
    monitor_id: str,
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> CheckResultRecord:
    """Run a check for a monitor now."""
    monitor = storage.get_monitor(monitor_id)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )

    final_status, message, total_elapsed_ms, all_details = _run_checks(monitor.url, monitor.checks)
    now = datetime.now(timezone.utc)

    # Create result record
    record = CheckResultRecord(
        id=str(uuid.uuid4()),
        monitor_id=monitor_id,
        status=final_status,
        message=message,
        elapsed_ms=total_elapsed_ms,
        details=all_details,
        checked_at=now,
    )

    # Save result and update monitor status
    storage.add_result(record)
    storage.update_monitor_status(monitor_id, final_status, now)

    return record


@router.get("/{monitor_id}/results", response_model=list[CheckResultRecord])
async def get_results(
    monitor_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    _user: str = Depends(require_auth),
    storage: Storage = Depends(get_storage),
) -> list[CheckResultRecord]:
    """Get check results for a monitor."""
    monitor = storage.get_monitor(monitor_id)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )
    return storage.get_results(monitor_id, limit=limit)
