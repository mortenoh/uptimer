# Uptimer

Service uptime monitoring CLI with pluggable checker system.

## Features

- Simple URL checking with `uptimer check`
- Follows redirects and shows full redirect chain
- Pluggable checker architecture
- JSON output for metrics and monitoring
- Rich terminal output with colors

## Quick Start

```bash
# Install
uv sync

# Check a URL
uptimer check google.com

# Verbose output
uptimer check google.com -v

# JSON output for metrics
uptimer --json check google.com
```

## Output Formats

### Console (default)

```
UP https://google.com (200)
```

### Verbose

```
UP https://google.com (200)
  Redirects:
    301 -> https://www.google.com/
  Final URL: https://www.google.com/
  Time: 1030ms
  HTTP: HTTP/1.1
  Server: gws
```

### JSON

```json
{"status": "up", "url": "https://google.com", "elapsed_ms": 934.67, ...}
```

## Status Codes

| Status | Color | Meaning |
|--------|-------|---------|
| UP | Green | HTTP status < 400 |
| DEGRADED | Yellow | HTTP status >= 400 |
| DOWN | Red | Connection error |

Exit code is `0` for UP/DEGRADED, `1` for DOWN.
