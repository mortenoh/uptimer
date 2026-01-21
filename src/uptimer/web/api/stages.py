"""Stages API routes."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from uptimer.stages import list_stages
from uptimer.web.api.deps import require_auth

router = APIRouter(prefix="/api/stages", tags=["stages"])


class StageOption(BaseModel):
    """Configuration option for a stage."""

    name: str = Field(..., description="Option name (matches Stage schema field)")
    label: str = Field(..., description="Human-readable label")
    type: str = Field(..., description="Option type: string, number, boolean, object")
    required: bool = Field(default=False, description="Whether option is required")
    default: Any = Field(default=None, description="Default value")
    description: str = Field(default="", description="Help text")
    placeholder: str = Field(default="", description="Placeholder text for inputs")


class StageInfo(BaseModel):
    """Information about a stage type."""

    type: str = Field(..., description="Stage type identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Stage description")
    is_network_stage: bool = Field(..., description="Whether stage makes network requests")
    options: list[StageOption] = Field(default_factory=list, description="Available options")  # pyright: ignore[reportUnknownVariableType]


# Stage metadata with options
STAGE_METADATA: dict[str, dict[str, Any]] = {
    "http": {
        "name": "HTTP",
        "description": "HTTP check with redirect following",
        "is_network_stage": True,
        "options": [
            {
                "name": "headers",
                "label": "Custom Headers",
                "type": "object",
                "description": "Custom HTTP headers to send",
                "placeholder": '{"Authorization": "Bearer token"}',
            },
        ],
    },
    "dhis2": {
        "name": "DHIS2",
        "description": "DHIS2 instance check with authentication",
        "is_network_stage": True,
        "options": [
            {
                "name": "username",
                "label": "Username",
                "type": "string",
                "default": "admin",
                "description": "DHIS2 username",
            },
            {
                "name": "password",
                "label": "Password",
                "type": "string",
                "default": "district",
                "description": "DHIS2 password",
            },
        ],
    },
    "ssl": {
        "name": "SSL Certificate",
        "description": "Check SSL certificate validity and expiration",
        "is_network_stage": True,
        "options": [
            {
                "name": "warn_days",
                "label": "Warning Days",
                "type": "number",
                "default": 30,
                "description": "Days before expiry to show warning",
            },
        ],
    },
    "tcp": {
        "name": "TCP Port",
        "description": "Check TCP port connectivity",
        "is_network_stage": True,
        "options": [
            {
                "name": "port",
                "label": "Port",
                "type": "number",
                "description": "Port to check (defaults to 80/443 based on URL)",
                "placeholder": "443",
            },
        ],
    },
    "dns": {
        "name": "DNS",
        "description": "Check DNS resolution",
        "is_network_stage": True,
        "options": [
            {
                "name": "expected_ip",
                "label": "Expected IP",
                "type": "string",
                "description": "Validate DNS resolves to this IP",
                "placeholder": "1.2.3.4",
            },
        ],
    },
    "contains": {
        "name": "Contains",
        "description": "Check if response contains/excludes text",
        "is_network_stage": False,
        "options": [
            {
                "name": "pattern",
                "label": "Pattern",
                "type": "string",
                "required": True,
                "description": "Text or regex to search for",
                "placeholder": "success",
            },
            {
                "name": "negate",
                "label": "Negate",
                "type": "boolean",
                "default": False,
                "description": "Fail if pattern IS found (expect absence)",
            },
        ],
    },
    "regex": {
        "name": "Regex",
        "description": "Match response against regex pattern",
        "is_network_stage": False,
        "options": [
            {
                "name": "pattern",
                "label": "Pattern",
                "type": "string",
                "required": True,
                "description": "Regular expression pattern",
                "placeholder": "version: \\d+\\.\\d+",
            },
            {
                "name": "negate",
                "label": "Negate",
                "type": "boolean",
                "default": False,
                "description": "Fail if pattern matches",
            },
        ],
    },
    "jsonpath": {
        "name": "JSONPath",
        "description": "Extract values using JSONPath expressions",
        "is_network_stage": False,
        "options": [
            {
                "name": "expr",
                "label": "Expression",
                "type": "string",
                "required": True,
                "description": "JSONPath expression",
                "placeholder": "$.data.count",
            },
            {
                "name": "store_as",
                "label": "Store As",
                "type": "string",
                "description": "Key to store extracted value for later stages",
                "placeholder": "count",
            },
        ],
    },
    "jq": {
        "name": "jq",
        "description": "Extract values using jq expressions",
        "is_network_stage": False,
        "options": [
            {
                "name": "expr",
                "label": "Expression",
                "type": "string",
                "required": True,
                "description": "jq expression",
                "placeholder": ".data | length",
            },
            {
                "name": "store_as",
                "label": "Store As",
                "type": "string",
                "description": "Key to store extracted value",
                "placeholder": "length",
            },
        ],
    },
    "threshold": {
        "name": "Threshold",
        "description": "Assert value is within bounds",
        "is_network_stage": False,
        "options": [
            {
                "name": "value",
                "label": "Value Reference",
                "type": "string",
                "default": "$elapsed_ms",
                "description": "Value to check ($elapsed_ms, $status_code, or stored key)",
                "placeholder": "$elapsed_ms",
            },
            {
                "name": "min",
                "label": "Minimum",
                "type": "number",
                "description": "Minimum allowed value",
            },
            {
                "name": "max",
                "label": "Maximum",
                "type": "number",
                "description": "Maximum allowed value",
                "placeholder": "1000",
            },
        ],
    },
    "age": {
        "name": "Age",
        "description": "Check data freshness (timestamp age)",
        "is_network_stage": False,
        "options": [
            {
                "name": "expr",
                "label": "Expression",
                "type": "string",
                "description": "JSONPath to timestamp field",
                "placeholder": "$.lastUpdated",
            },
            {
                "name": "max_age",
                "label": "Max Age (seconds)",
                "type": "number",
                "required": True,
                "description": "Maximum allowed age in seconds",
                "placeholder": "3600",
            },
        ],
    },
    "header": {
        "name": "Header",
        "description": "Check response header values",
        "is_network_stage": False,
        "options": [
            {
                "name": "pattern",
                "label": "Header: Value",
                "type": "string",
                "required": True,
                "description": "Header name and expected value",
                "placeholder": "Content-Type: application/json",
            },
            {
                "name": "negate",
                "label": "Negate",
                "type": "boolean",
                "default": False,
                "description": "Fail if header matches",
            },
        ],
    },
    "json_schema": {
        "name": "JSON Schema",
        "description": "Validate response against JSON Schema",
        "is_network_stage": False,
        "options": [
            {
                "name": "schema",
                "label": "Schema",
                "type": "object",
                "required": True,
                "description": "JSON Schema to validate against",
                "placeholder": '{"type": "object", "required": ["id"]}',
            },
        ],
    },
    "dhis2_checks": {
        "name": "DHIS2 Checks",
        "description": "Run DHIS2 system checks endpoint",
        "is_network_stage": True,
        "options": [
            {
                "name": "username",
                "label": "Username",
                "type": "string",
                "default": "admin",
                "description": "DHIS2 username",
            },
            {
                "name": "password",
                "label": "Password",
                "type": "string",
                "default": "district",
                "description": "DHIS2 password",
            },
        ],
    },
}


@router.get("", response_model=list[StageInfo])
async def get_stages(_user: str = Depends(require_auth)) -> list[StageInfo]:
    """Get all available stage types with their configuration options."""
    stages: list[StageInfo] = []
    for stage_type in list_stages():
        metadata = STAGE_METADATA.get(stage_type, {})
        options_data: list[dict[str, Any]] = metadata.get("options", [])
        stages.append(
            StageInfo(
                type=stage_type,
                name=metadata.get("name", stage_type),
                description=metadata.get("description", ""),
                is_network_stage=metadata.get("is_network_stage", False),
                options=[StageOption(**opt) for opt in options_data],
            )
        )
    return stages
