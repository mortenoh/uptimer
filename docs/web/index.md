# Web UI

Uptimer includes a web-based dashboard for monitoring services.

## Quick Start

```bash
# Start the web server
uptimer serve

# Or use make
make serve
```

The server starts at `http://127.0.0.1:8000` by default.

## Login

Default credentials:

- **Username:** `admin`
- **Password:** `admin`

!!! warning "Change Default Credentials"
    Always change the default credentials in production. See [Configuration](configuration.md).

## Features

### Dashboard

The dashboard provides:

- Overview of monitored services
- Quick check for ad-hoc URL testing
- Service status at a glance

### Quick Check

Test any URL directly from the dashboard:

1. Enter a URL in the Quick Check form
2. Click "Check"
3. See the result with status, response time, and details

### REST API

The web UI exposes a REST API for programmatic access. All endpoints require authentication.

#### Monitors

```bash
# List all monitors
curl -b cookies.txt "http://localhost:8000/api/monitors"

# List monitors filtered by tag
curl -b cookies.txt "http://localhost:8000/api/monitors?tag=production"

# List all tags
curl -b cookies.txt "http://localhost:8000/api/monitors/tags"

# Create a monitor
curl -X POST -b cookies.txt "http://localhost:8000/api/monitors" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Service",
    "url": "https://example.com",
    "pipeline": [{"type": "http"}],
    "tags": ["production", "api"],
    "interval": 60
  }'

# Get a monitor
curl -b cookies.txt "http://localhost:8000/api/monitors/{id}"

# Update a monitor
curl -X PUT -b cookies.txt "http://localhost:8000/api/monitors/{id}" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["production", "api", "critical"]}'

# Delete a monitor
curl -X DELETE -b cookies.txt "http://localhost:8000/api/monitors/{id}"

# Run a check
curl -X POST -b cookies.txt "http://localhost:8000/api/monitors/{id}/check"

# Get check results
curl -b cookies.txt "http://localhost:8000/api/monitors/{id}/results?limit=100"
```

#### Monitor Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Display name (1-100 chars) |
| `url` | string | Yes | - | URL to monitor |
| `pipeline` | array | No | `[{"type": "http"}]` | Array of stage configurations |
| `interval` | int | No | `30` | Check interval in seconds (min 10) |
| `schedule` | string | No | `null` | Cron schedule (alternative to interval) |
| `enabled` | bool | No | `true` | Whether monitor is active |
| `tags` | list | No | `[]` | Tags for grouping/filtering |

#### Quick Check

```bash
# Check a URL (requires authentication)
curl -b cookies.txt "http://localhost:8000/api/check?url=google.com"
```

Response:

```json
{
  "status": "up",
  "url": "https://google.com",
  "message": "200",
  "elapsed_ms": 934.67,
  "status_code": 200,
  "final_url": "https://www.google.com/"
}
```

## CLI Options

```bash
uptimer serve [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--host` | `-h` | `127.0.0.1` | Host to bind to |
| `--port` | `-p` | `8000` | Port to bind to |
| `--reload` | `-r` | `false` | Enable auto-reload for development |

### Examples

```bash
# Bind to all interfaces
uptimer serve --host 0.0.0.0

# Use a different port
uptimer serve --port 3000

# Development mode with auto-reload
uptimer serve --reload
```
