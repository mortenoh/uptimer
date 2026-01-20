"""Pydantic models for monitors and check results."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MonitorCreate(BaseModel):
    """Model for creating a new monitor."""

    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    url: str = Field(..., description="URL to check")
    checker: str = Field(default="http", description="Checker type")
    username: str | None = Field(default=None, description="Auth username (optional)")
    password: str | None = Field(default=None, description="Auth password (optional)")
    interval: int = Field(default=60, ge=10, description="Check interval in seconds")
    enabled: bool = Field(default=True, description="Whether monitor is active")

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate name is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip()


class MonitorUpdate(BaseModel):
    """Model for updating a monitor. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = None
    checker: str | None = None
    username: str | None = None
    password: str | None = None
    interval: int | None = Field(default=None, ge=10)
    enabled: bool | None = None

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
    interval: int = 60
    enabled: bool = True
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
