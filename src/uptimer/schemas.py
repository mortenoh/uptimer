"""Pydantic models for monitors and check results."""

from datetime import datetime
from typing import Any

from croniter import croniter
from pydantic import BaseModel, Field, field_validator


class MonitorCreate(BaseModel):
    """Model for creating a new monitor."""

    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    url: str = Field(..., description="URL to check")
    checker: str = Field(default="http", description="Checker type")
    username: str | None = Field(default=None, description="Auth username (optional)")
    password: str | None = Field(default=None, description="Auth password (optional)")
    interval: int = Field(default=30, ge=10, description="Check interval in seconds")
    schedule: str | None = Field(default=None, description="Cron expression (e.g. '*/5 * * * *')")
    enabled: bool = Field(default=True, description="Whether monitor is active")
    tags: list[str] = Field(default_factory=list, description="Tags for grouping/filtering")

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate name is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip()

    @field_validator("schedule")
    @classmethod
    def validate_cron_expression(cls, v: str | None) -> str | None:
        """Validate cron expression if provided."""
        if v is not None:
            if not croniter.is_valid(v):
                raise ValueError(f"Invalid cron expression: {v}")
        return v


class MonitorUpdate(BaseModel):
    """Model for updating a monitor. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = None
    checker: str | None = None
    username: str | None = None
    password: str | None = None
    interval: int | None = Field(default=None, ge=10)
    schedule: str | None = None
    enabled: bool | None = None
    tags: list[str] | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str | None) -> str | None:
        """Validate name is not empty or whitespace only."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip() if v else v


class Monitor(BaseModel):
    """Full monitor model with all fields."""

    id: str
    name: str
    url: str
    checker: str = "http"
    username: str | None = None
    password: str | None = None
    interval: int = 30
    schedule: str | None = None
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_check: datetime | None = None
    last_status: str | None = None


class CheckResultRecord(BaseModel):
    """Record of a check result."""

    id: str
    monitor_id: str
    status: str
    message: str
    elapsed_ms: float
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime
