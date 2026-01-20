# Uptimer

Service uptime monitoring CLI.

## Installation

```bash
uv sync
```

## Usage

### Check a URL

```bash
uptimer check google.com
uptimer check https://example.com
```

Output:
```
UP https://google.com (200)
```

### Verbose mode

Show redirect chain, response time, and headers:

```bash
uptimer check google.com -v
```

Output:
```
UP https://google.com (200)
  Redirects:
    301 -> https://www.google.com/
  Final URL: https://www.google.com/
  Time: 1030ms
  HTTP: HTTP/1.1
  Server: gws
  Content-Type: text/html; charset=ISO-8859-1
```

### List available checkers

```bash
uptimer checkers
```

Output:
```
  http - HTTP check with redirect following
```

### Specify a checker

```bash
uptimer check google.com -c http
```

## Status codes

- **UP** (green) - HTTP status < 400
- **DEGRADED** (yellow) - HTTP status >= 400
- **DOWN** (red) - Connection error

Exit code is 0 for UP/DEGRADED, 1 for DOWN.

## Development

```bash
make install    # Install dependencies
make lint       # Run ruff + mypy + pyright
make test       # Run tests
make coverage   # Run tests with coverage
make clean      # Clean temp files
```

## Architecture

### Pluggable checker system

Checkers are pluggable via `src/uptimer/checkers/`:

- `base.py` - `Checker` base class and `CheckResult` dataclass
- `http.py` - Default HTTP checker with redirect following
- `registry.py` - Checker registration and lookup

To add a new checker:

1. Create a new file in `src/uptimer/checkers/`
2. Subclass `Checker` and implement `check()`
3. Register with `@register_checker` decorator or call `register_checker()`

Example:

```python
from uptimer.checkers.base import Checker, CheckResult, Status
from uptimer.checkers.registry import register_checker

@register_checker
class MyChecker(Checker):
    name = "my-checker"
    description = "My custom checker"

    def check(self, url: str, verbose: bool = False) -> CheckResult:
        # ... perform check ...
        return CheckResult(
            status=Status.UP,
            url=url,
            message="OK",
            elapsed_ms=100.0,
            details={"custom": "data"},
        )
```

## Planned features

- DHIS2 checker (with authentication)
- Multiple URL checks
- Configuration file support
- Scheduled monitoring
- Web UI with login
