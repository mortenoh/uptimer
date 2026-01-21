"""JSON Schema stage - validates response against a JSON schema."""

import json
from typing import Any

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


def _validate_type(value: Any, expected_type: str) -> bool:
    """Validate a value against a JSON Schema type."""
    type_map: dict[str, type | tuple[type, ...]] = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }
    expected = type_map.get(expected_type)
    if expected is None:
        return True
    return isinstance(value, expected)


def _validate_schema(data: Any, schema: dict[str, Any], path: str = "") -> list[str]:
    """Validate data against a JSON schema.

    Simple implementation supporting:
    - type validation
    - required properties
    - properties validation
    - items validation for arrays
    - minimum/maximum for numbers
    - minLength/maxLength for strings
    - enum validation

    Args:
        data: Data to validate
        schema: JSON schema
        path: Current path in the data structure

    Returns:
        List of validation errors
    """
    errors: list[str] = []

    # Type validation
    if "type" in schema:
        expected_type = schema["type"]
        if isinstance(expected_type, list):
            type_list: list[str] = expected_type  # pyright: ignore[reportUnknownVariableType]
            if not any(_validate_type(data, t) for t in type_list):
                errors.append(f"{path}: expected type {expected_type}, got {type(data).__name__}")
        elif isinstance(expected_type, str) and not _validate_type(data, expected_type):
            errors.append(f"{path}: expected type {expected_type}, got {type(data).__name__}")

    # Enum validation
    if "enum" in schema:
        if data not in schema["enum"]:
            errors.append(f"{path}: value {data!r} not in enum {schema['enum']}")

    # Object validation
    if isinstance(data, dict):
        # Required properties
        if "required" in schema:
            for prop in schema["required"]:
                if prop not in data:
                    errors.append(f"{path}: missing required property '{prop}'")

        # Properties validation
        if "properties" in schema:
            for prop, prop_schema in schema["properties"].items():
                if prop in data:
                    errors.extend(_validate_schema(data[prop], prop_schema, f"{path}.{prop}"))

    # Array validation
    if isinstance(data, list) and "items" in schema:
        data_list: list[Any] = data  # pyright: ignore[reportUnknownVariableType]
        for i, item in enumerate(data_list):
            errors.extend(_validate_schema(item, schema["items"], f"{path}[{i}]"))

    # Number validation
    if isinstance(data, (int, float)):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} > maximum {schema['maximum']}")

    # String validation
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path}: length {len(data)} < minLength {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(f"{path}: length {len(data)} > maxLength {schema['maxLength']}")
        if "pattern" in schema:
            import re

            if not re.match(schema["pattern"], data):
                errors.append(f"{path}: does not match pattern {schema['pattern']}")

    return errors


@register_stage
class JsonSchemaStage(Stage):
    """Validate response body against a JSON schema."""

    name = "json-schema"
    description = "Validate response against JSON schema"
    is_network_stage = False

    def __init__(self, schema: dict[str, Any] | None = None) -> None:
        """Initialize JSON schema stage.

        Args:
            schema: JSON schema to validate against
        """
        self.schema = schema or {}

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Validate response body against JSON schema."""
        if context is None or context.response_body is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No response body to validate",
                details={"error": "Context or response body missing"},
            )

        if not self.schema:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No schema specified",
                details={"error": "Schema is required"},
            )

        try:
            data = json.loads(context.response_body)
        except json.JSONDecodeError as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="Invalid JSON response",
                details={"error": str(e)},
            )

        errors = _validate_schema(data, self.schema)

        if errors:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Schema validation failed: {len(errors)} errors",
                details={"errors": errors, "error_count": len(errors)},
            )

        return CheckResult(
            status=Status.UP,
            url=url,
            message="Schema validation passed",
            details={"valid": True},
        )
