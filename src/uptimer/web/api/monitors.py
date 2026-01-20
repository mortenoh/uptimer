"""Monitor API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from uptimer.checkers import get_checker
from uptimer.schemas import CheckResultRecord, Monitor, MonitorCreate, MonitorUpdate
from uptimer.storage import Storage
from uptimer.web.api.deps import get_storage, require_auth

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


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

        # Get checker and run check
        checker_class = get_checker(monitor.checker)

        if monitor.username and monitor.password:
            try:
                checker = checker_class(username=monitor.username, password=monitor.password)
            except TypeError:
                checker = checker_class()
        else:
            checker = checker_class()

        result = checker.check(monitor.url, verbose=False)
        now = datetime.now(timezone.utc)

        record = CheckResultRecord(
            id=str(uuid.uuid4()),
            monitor_id=monitor.id,
            status=result.status.value,
            message=result.message,
            elapsed_ms=result.elapsed_ms,
            details=result.details,
            checked_at=now,
        )

        storage.add_result(record)
        storage.update_monitor_status(monitor.id, result.status.value, now)
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

    # Get checker and run check
    checker_class = get_checker(monitor.checker)

    # Instantiate checker with credentials if available (for checkers like dhis2)
    if monitor.username and monitor.password:
        try:
            # Some checkers accept credentials (e.g., dhis2)
            checker = checker_class(username=monitor.username, password=monitor.password)  # type: ignore[call-arg]
        except TypeError:
            # Checker doesn't support credentials
            checker = checker_class()
    else:
        checker = checker_class()

    result = checker.check(monitor.url, verbose=False)

    now = datetime.now(timezone.utc)

    # Create result record
    record = CheckResultRecord(
        id=str(uuid.uuid4()),
        monitor_id=monitor_id,
        status=result.status.value,
        message=result.message,
        elapsed_ms=result.elapsed_ms,
        details=result.details,
        checked_at=now,
    )

    # Save result and update monitor status
    storage.add_result(record)
    storage.update_monitor_status(monitor_id, result.status.value, now)

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
