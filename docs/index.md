# Uptimer

Service uptime monitoring with pluggable stage system, REST API, and React dashboard.

## Features

- Monitor management via CLI and REST API
- Pipeline-based checks with 15+ stage types
- Value extraction (jq, jsonpath, regex) and assertions
- SSL certificate monitoring
- React dashboard with dark theme
- JSON output for automation
- Tag-based organization

**New to Uptimer?** Start with the [Introduction Guide](introduction.md).

## Quick Start

```bash
# Install
uv sync

# Start MongoDB (required for storage)
docker run -d -p 27017:27017 mongo:7

# Start the server
uptimer serve

# Add a monitor
uptimer add "Google" https://google.com

# Run a check
uptimer check <monitor-id>

# List monitors
uptimer list
```

## Architecture

```
CLI (client) --> REST API --> MongoDB
                    |
              Web Dashboard
```

The CLI is a thin client that communicates with the backend via REST API. All monitor data is stored in MongoDB.

## CLI Commands

| Command | Description |
|---------|-------------|
| `uptimer list` | List all monitors |
| `uptimer add NAME URL` | Create a monitor |
| `uptimer get ID` | Get monitor details |
| `uptimer delete ID` | Delete a monitor |
| `uptimer check ID` | Run check for a monitor |
| `uptimer check-all` | Run all checks |
| `uptimer results ID` | View check history |
| `uptimer tags` | List all tags |
| `uptimer stages` | List available stages |
| `uptimer serve` | Start the server |

## Status Codes

| Status | Color | Meaning |
|--------|-------|---------|
| UP | Green | All checks passed |
| DEGRADED | Yellow | Some checks have warnings |
| DOWN | Red | Check failed |

## Output Formats

All commands support `--json` flag for machine-readable output:

```bash
uptimer --json list
uptimer --json check abc123
```
