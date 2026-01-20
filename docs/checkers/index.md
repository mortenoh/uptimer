# Checkers

Uptimer uses a pluggable checker system. Each checker is responsible for performing a specific type of health check.

## Available Checkers

| Name | Description |
|------|-------------|
| `http` | HTTP check with redirect following |

## Using Checkers

Specify a checker with the `-c` or `--checker` option:

```bash
uptimer check example.com -c http
```

List all available checkers:

```bash
uptimer checkers
```

## Checker Output

All checkers return a `CheckResult` with:

- `status` - UP, DEGRADED, or DOWN
- `url` - The checked URL
- `message` - Status message (e.g., HTTP status code)
- `elapsed_ms` - Time taken in milliseconds
- `details` - Checker-specific details
