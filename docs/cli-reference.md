# CLI Reference

The CLI is a thin client that manages monitors and triggers checks via the REST API.

## Configuration

The CLI uses these settings from `config.yaml` or environment variables:

| Setting | Env Variable | Default | Description |
|---------|--------------|---------|-------------|
| `api_url` | `UPTIMER_API_URL` | `http://localhost:8000` | API server URL |
| `username` | `UPTIMER_USERNAME` | `admin` | API username |
| `password` | `UPTIMER_PASSWORD` | `admin` | API password |

## Global Options

### `--version`

Show version and exit.

```bash
uptimer --version
```

### `--json`

Output as JSON instead of rich console output. Works with all commands.

```bash
uptimer --json list
uptimer --json check abc123
```

## Commands

### `list`

List all monitors.

```bash
uptimer list [OPTIONS]
```

**Options:**

- `-t`, `--tag TAG` - Filter by tag

**Examples:**

```bash
# List all monitors
uptimer list

# Filter by tag
uptimer list --tag production

# JSON output
uptimer --json list
```

**Output:**

```
ID        Name        URL                     Status  Last Check
abc123    Google      https://google.com      up      2m ago
def456    API         https://api.example.com down    5m ago
```

### `get`

Get monitor details.

```bash
uptimer get MONITOR_ID
```

**Arguments:**

- `MONITOR_ID` - The monitor ID (required)

**Examples:**

```bash
uptimer get abc123
uptimer --json get abc123
```

### `add`

Create a new monitor.

```bash
uptimer add [OPTIONS] NAME URL
```

**Arguments:**

- `NAME` - Monitor display name (required)
- `URL` - URL to monitor (required)

**Options:**

- `-c`, `--stage TYPE` - Checker type (can be repeated, default: `http`)
- `-t`, `--tag TAG` - Tag (can be repeated)
- `-i`, `--interval SECONDS` - Check interval in seconds (default: 30)
- `-s`, `--schedule CRON` - Cron schedule expression

**Examples:**

```bash
# Basic monitor
uptimer add "Google" https://google.com

# With multiple checks
uptimer add "My Site" https://example.com --stage http --stage ssl

# With tags and interval
uptimer add "Production API" https://api.example.com \
  --tag production --tag api --interval 60

# With cron schedule
uptimer add "Hourly Check" https://example.com --schedule "0 * * * *"
```

### `delete`

Delete a monitor.

```bash
uptimer delete [OPTIONS] MONITOR_ID
```

**Arguments:**

- `MONITOR_ID` - The monitor ID (required)

**Options:**

- `-f`, `--force` - Skip confirmation prompt

**Examples:**

```bash
# With confirmation
uptimer delete abc123

# Skip confirmation
uptimer delete abc123 --force
```

### `check`

Run a check for a monitor immediately.

```bash
uptimer check MONITOR_ID
```

**Arguments:**

- `MONITOR_ID` - The monitor ID (required)

**Examples:**

```bash
uptimer check abc123
uptimer --json check abc123
```

**Output:**

```
UP http: 200 OK (145ms)
```

### `check-all`

Run checks for all monitors.

```bash
uptimer check-all [OPTIONS]
```

**Options:**

- `-t`, `--tag TAG` - Only check monitors with this tag

**Examples:**

```bash
# Check all monitors
uptimer check-all

# Check only production monitors
uptimer check-all --tag production
```

### `results`

Get check history for a monitor.

```bash
uptimer results [OPTIONS] MONITOR_ID
```

**Arguments:**

- `MONITOR_ID` - The monitor ID (required)

**Options:**

- `-n`, `--limit N` - Number of results (default: 10)

**Examples:**

```bash
uptimer results abc123
uptimer results abc123 --limit 50
uptimer --json results abc123
```

### `tags`

List all unique tags.

```bash
uptimer tags
```

**Examples:**

```bash
uptimer tags
uptimer --json tags
```

### `stages`

List available stage types.

```bash
uptimer stages
```

This command runs locally and does not require the API server.

**Output:**

```
  http - HTTP check with redirect following
  dhis2 - DHIS2 instance check with authentication
  ssl - SSL certificate expiry check
  jq - Extract values using jq expressions
  threshold - Assert values within bounds
```

### `serve`

Start the web UI server.

```bash
uptimer serve [OPTIONS]
```

**Options:**

- `-h`, `--host HOST` - Host to bind to (default: `127.0.0.1`)
- `-p`, `--port PORT` - Port to bind to (default: `8000`)
- `-r`, `--reload` - Enable auto-reload for development

**Examples:**

```bash
# Default settings
uptimer serve

# Custom host and port
uptimer serve --host 0.0.0.0 --port 9000

# Development mode with auto-reload
uptimer serve --reload
```

### `init`

Initialize configuration file by copying `config.example.yaml` to `config.yaml`.

```bash
uptimer init
```

### `version`

Show version information.

```bash
uptimer version
```
