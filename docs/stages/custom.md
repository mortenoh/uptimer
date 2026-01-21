# Custom Stages

Create custom stages by subclassing `Stage` and registering with the registry.

## Creating a Stage

```python
from uptimer.stages.base import Stage, CheckResult, Status
from uptimer.stages.registry import register_stage


@register_stage
class MyStage(Stage):
    """My custom stage."""

    name = "my-stage"
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

## Stage Base Class

::: uptimer.stages.base.Stage
    options:
      show_source: true

## CheckResult

::: uptimer.stages.base.CheckResult
    options:
      show_source: true

## Status Enum

::: uptimer.stages.base.Status
    options:
      show_source: true

## Registry Functions

### register_stage

Register a stage class with the registry.

```python
from uptimer.stages.registry import register_stage

@register_stage
class MyStage(Stage):
    ...
```

### get_stage

Get a stage class by name.

```python
from uptimer.stages.registry import get_stage

stage_class = get_stage("http")
stage = stage_class()
result = stage.check("https://example.com")
```

### list_stages

List all registered stage names.

```python
from uptimer.stages.registry import list_stages

names = list_stages()  # ["http", "my-stage"]
```
