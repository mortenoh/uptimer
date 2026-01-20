# Custom Checkers

Create custom checkers by subclassing `Checker` and registering with the registry.

## Creating a Checker

```python
from uptimer.checkers.base import Checker, CheckResult, Status
from uptimer.checkers.registry import register_checker


@register_checker
class MyChecker(Checker):
    """My custom checker."""

    name = "my-checker"
    description = "My custom health check"

    def check(self, url: str, verbose: bool = False) -> CheckResult:
        """Perform the check."""
        # Your check logic here
        return CheckResult(
            status=Status.UP,
            url=url,
            message="OK",
            elapsed_ms=100.0,
            details={"custom": "data"},
        )
```

## Checker Base Class

::: uptimer.checkers.base.Checker
    options:
      show_source: true

## CheckResult

::: uptimer.checkers.base.CheckResult
    options:
      show_source: true

## Status Enum

::: uptimer.checkers.base.Status
    options:
      show_source: true

## Registry Functions

### register_checker

Register a checker class with the registry.

```python
from uptimer.checkers.registry import register_checker

@register_checker
class MyChecker(Checker):
    ...
```

### get_checker

Get a checker class by name.

```python
from uptimer.checkers.registry import get_checker

checker_class = get_checker("http")
checker = checker_class()
result = checker.check("https://example.com")
```

### list_checkers

List all registered checker names.

```python
from uptimer.checkers.registry import list_checkers

names = list_checkers()  # ["http", "my-checker"]
```
