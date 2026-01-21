# API Reference

## Stages

### Base Classes

::: uptimer.stages.base
    options:
      show_source: true
      members:
        - Status
        - CheckResult
        - CheckContext
        - Stage

### HTTP Stage

::: uptimer.stages.http.HttpStage
    options:
      show_source: true

### Registry

::: uptimer.stages.registry
    options:
      show_source: true
      members:
        - register_stage
        - get_stage
        - list_stages

## Logging

::: uptimer.logging
    options:
      show_source: true
      members:
        - configure_logging
        - get_logger
