"""JQ stage - extracts values from JSON responses using jq-like expressions."""

import json
import re
from typing import Any

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


def _jq_extract(data: Any, expr: str) -> Any:
    """Extract value from data using a simplified jq-like expression.

    Supports:
    - .key - access object key
    - .key.nested - nested access
    - .[0] - array index
    - .key[0] - combined access
    - .key | length - pipe to length function
    - .key | keys - pipe to keys function

    Args:
        data: JSON data (dict, list, or primitive)
        expr: jq-like expression

    Returns:
        Extracted value
    """
    if not expr or expr == ".":
        return data

    # Handle pipes (simple case)
    if " | " in expr:
        parts = expr.split(" | ")
        value: Any = _jq_extract(data, parts[0])
        for func in parts[1:]:
            func = func.strip()
            if func == "length":
                value = len(value) if isinstance(value, (str, list, dict, tuple)) else 0  # pyright: ignore[reportUnknownArgumentType]
            elif func == "keys":
                value = list(value.keys()) if isinstance(value, dict) else []  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType]
            elif func == "type":
                value = type(value).__name__  # pyright: ignore[reportUnknownArgumentType]
            elif func == "first":
                value = value[0] if isinstance(value, list) and len(value) > 0 else None  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType]
            elif func == "last":
                value = value[-1] if isinstance(value, list) and len(value) > 0 else None  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType]
        return value  # pyright: ignore[reportUnknownVariableType]

    # Remove leading dot
    if expr.startswith("."):
        expr = expr[1:]

    current: Any = data

    # Parse expression into tokens
    # Matches: key, [0], ["key"]
    tokens: list[tuple[str, str, str]] = re.findall(r'(\w+)|\[(\d+)\]|\["([^"]+)"\]', expr)

    for token in tokens:
        key, index, quoted_key = token

        if key:
            if isinstance(current, dict):
                current = current.get(key)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            else:
                return None
        elif index:
            idx = int(index)
            if isinstance(current, (list, tuple)) and 0 <= idx < len(current):  # pyright: ignore[reportUnknownArgumentType]
                current = current[idx]  # pyright: ignore[reportUnknownVariableType]
            else:
                return None
        elif quoted_key:
            if isinstance(current, dict):
                current = current.get(quoted_key)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            else:
                return None

        if current is None:
            return None

    return current  # pyright: ignore[reportUnknownVariableType]


@register_stage
class JqStage(Stage):
    """Extract values from JSON response using jq-like expressions."""

    name = "jq"
    description = "Extract values from JSON using jq expressions"
    is_network_stage = False

    def __init__(self, expr: str = ".", store_as: str | None = None) -> None:
        """Initialize with expression.

        Args:
            expr: jq-like expression (e.g., ".data.count", ".items[0].name")
            store_as: Key to store extracted value in context
        """
        self.expr = expr
        self.store_as = store_as

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Extract value from JSON response body."""
        if context is None or context.response_body is None:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message="No response body to extract from",
                details={"error": "Context or response body missing"},
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

        try:
            value = _jq_extract(data, self.expr)

            # Store in context if store_as is specified
            if self.store_as:
                context.values[self.store_as] = value

            return CheckResult(
                status=Status.UP,
                url=url,
                message=f"extracted: {value}",
                details={
                    "expression": self.expr,
                    "value": value,
                    "type": type(value).__name__ if value is not None else "null",
                },
            )

        except Exception as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"Extraction failed: {e}",
                details={"expression": self.expr, "error": str(e)},
            )
