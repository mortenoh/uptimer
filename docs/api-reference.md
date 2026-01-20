# API Reference

## Checkers

### Base Classes

::: uptimer.checkers.base
    options:
      show_source: true
      members:
        - Status
        - CheckResult
        - Checker

### HTTP Checker

::: uptimer.checkers.http.HttpChecker
    options:
      show_source: true

### Registry

::: uptimer.checkers.registry
    options:
      show_source: true
      members:
        - register_checker
        - get_checker
        - list_checkers

## Logging

::: uptimer.logging
    options:
      show_source: true
      members:
        - configure_logging
        - get_logger
