"""JSONPath stage - extracts values using JSONPath expressions."""

import json
import re
from typing import Any

from uptimer.stages.base import CheckContext, CheckResult, Stage, Status
from uptimer.stages.registry import register_stage


def _jsonpath_extract(data: Any, expr: str) -> list[Any]:
    """Extract values using JSONPath expression.

    Supports subset of JSONPath:
    - $ - root object
    - .key - child operator
    - ..key - recursive descent
    - [n] - array index
    - [*] - wildcard (all items)
    - [start:end] - array slice

    Args:
        data: JSON data
        expr: JSONPath expression starting with $

    Returns:
        List of matched values
    """
    if not expr.startswith("$"):
        return []

    # Remove leading $
    expr = expr[1:]

    def _extract(current: Any, path: str) -> list[Any]:
        if not path:
            return [current]

        # Remove leading dot
        if path.startswith("."):
            path = path[1:]

        # Recursive descent
        if path.startswith("."):
            path = path[1:]
            key_match = re.match(r"^(\w+)(.*)", path)
            if key_match:
                key, rest = key_match.groups()

                def _recurse(obj: Any) -> list[Any]:
                    found: list[Any] = []
                    if isinstance(obj, dict):
                        if key in obj:
                            found.extend(_extract(obj[key], rest))
                        for v in obj.values():  # pyright: ignore[reportUnknownVariableType]
                            found.extend(_recurse(v))
                    elif isinstance(obj, list):
                        for item in obj:  # pyright: ignore[reportUnknownVariableType]
                            found.extend(_recurse(item))
                    return found

                return _recurse(current)
            return []

        # Array access
        if path.startswith("["):
            bracket_end = path.find("]")
            if bracket_end == -1:
                return []
            index_str = path[1:bracket_end]
            rest = path[bracket_end + 1 :]

            if not isinstance(current, list):
                return []

            # Wildcard
            if index_str == "*":
                wildcard_results: list[Any] = []
                for item in current:  # pyright: ignore[reportUnknownVariableType]
                    wildcard_results.extend(_extract(item, rest))
                return wildcard_results

            # Slice
            if ":" in index_str:
                parts = index_str.split(":")
                start = int(parts[0]) if parts[0] else None
                end = int(parts[1]) if parts[1] else None
                sliced: list[Any] = current[start:end]  # pyright: ignore[reportUnknownVariableType]
                slice_results: list[Any] = []
                for item in sliced:
                    slice_results.extend(_extract(item, rest))
                return slice_results

            # Index
            try:
                idx = int(index_str)
                current_list: list[Any] = current  # pyright: ignore[reportUnknownVariableType]
                if 0 <= idx < len(current_list):
                    return _extract(current_list[idx], rest)
            except ValueError:
                pass
            return []

        # Key access
        key_match = re.match(r"^(\w+)(.*)", path)
        if key_match:
            key, rest = key_match.groups()
            if isinstance(current, dict) and key in current:
                return _extract(current[key], rest)
            return []

        return []

    return _extract(data, expr)


@register_stage
class JsonPathStage(Stage):
    """Extract values using JSONPath expressions."""

    name = "jsonpath"
    description = "Extract values using JSONPath expressions"
    is_network_stage = False

    def __init__(self, expr: str = "$", store_as: str | None = None) -> None:
        """Initialize JSONPath stage.

        Args:
            expr: JSONPath expression (e.g., "$.store.book[0].title")
            store_as: Key to store extracted value in context
        """
        self.expr = expr
        self.store_as = store_as

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        """Extract values using JSONPath."""
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
            matches = _jsonpath_extract(data, self.expr)

            if not matches:
                return CheckResult(
                    status=Status.DOWN,
                    url=url,
                    message=f"No matches for: {self.expr}",
                    details={"expression": self.expr, "matches": []},
                )

            # Store first match in context
            value = matches[0] if len(matches) == 1 else matches
            if self.store_as:
                context.values[self.store_as] = value

            return CheckResult(
                status=Status.UP,
                url=url,
                message=f"extracted: {value}",
                details={
                    "expression": self.expr,
                    "value": value,
                    "match_count": len(matches),
                    "matches": matches[:10],  # Limit to first 10 matches
                },
            )

        except Exception as e:
            return CheckResult(
                status=Status.DOWN,
                url=url,
                message=f"JSONPath error: {e}",
                details={"expression": self.expr, "error": str(e)},
            )
