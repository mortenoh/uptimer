# Uptimer

Service uptime monitoring with a modern React dashboard.

## Features

- REST API for monitor management
- Modern React + shadcn/ui dashboard with dark theme
- MongoDB storage for monitors and results
- Pluggable stage system with 15+ check types
- Value extractors and transformers (jq, regex, jsonpath)
- Threshold assertions and content validation
- SSL certificate monitoring
- DHIS2-specific health checks
- Tag-based organization and filtering
- Docker Compose deployment

## Quick Start

### Using Docker Compose

```bash
docker-compose up -d
```

This starts:
- MongoDB on port 27017
- API server on port 8000
- Frontend on port 3000

Open http://localhost:3000 and login with `admin` / `admin`.

### Local Development

```bash
# Install dependencies
uv sync

# Start MongoDB
docker run -d -p 27017:27017 mongo

# Run API server
make serve

# In another terminal, run frontend
cd clients/web
npm install
npm run dev
```

## Available Stages

### Network Checks

| Stage | Description | Options |
|-------|-------------|---------|
| `http` | HTTP request with redirect following | `timeout`, `headers` |
| `ssl` | SSL certificate validity check | `warn_days` (default: 30) |
| `tcp` | TCP port connectivity | `port` |
| `dns` | DNS resolution check | `expected_ip` |

### Value Extractors

| Stage | Description | Options |
|-------|-------------|---------|
| `jq` | Extract from JSON using jq syntax | `expr`, `store_as` |
| `jsonpath` | Extract using JSONPath syntax | `expr`, `store_as` |
| `regex` | Extract using regex capture groups | `pattern`, `store_as` |
| `header` | Extract HTTP response headers | `pattern` (header name), `store_as` |

### Assertions

| Stage | Description | Options |
|-------|-------------|---------|
| `threshold` | Assert value within bounds | `value`, `min`, `max` |
| `contains` | Check response contains text | `pattern`, `negate` |
| `age` | Validate timestamp freshness | `value`, `max_age` |
| `json-schema` | Validate against JSON schema | `schema` |

### DHIS2 Checks

| Stage | Description | Options |
|-------|-------------|---------|
| `dhis2` | DHIS2 system info check | `username`, `password` |
| `dhis2-version` | Version requirement check | `username`, `password`, `min_version` |
| `dhis2-integrity` | Data integrity checks | `username`, `password` |
| `dhis2-job` | Scheduled job status | `username`, `password`, `job_type` |
| `dhis2-analytics` | Analytics table freshness | `username`, `password`, `max_age_hours` |

## API Examples

### Create a monitor

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google",
    "url": "https://www.google.com",
    "pipeline": [{"type": "http"}],
    "interval": 30,
    "tags": ["search", "public"]
  }'
```

### Create monitor with chained checks

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Health",
    "url": "https://api.example.com/health",
    "pipeline": [
      {"type": "http"},
      {"type": "jq", "expr": ".status", "store_as": "status"},
      {"type": "threshold", "value": "$elapsed_ms", "max": 2000}
    ],
    "tags": ["api", "critical"]
  }'
```

### Create monitor with custom headers

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Protected API",
    "url": "https://api.example.com/data",
    "pipeline": [
      {"type": "http", "headers": {"Authorization": "Bearer your-token", "X-API-Key": "key123"}}
    ],
    "tags": ["api", "protected"]
  }'
```

### Create DHIS2 monitor

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DHIS2 Demo",
    "url": "https://play.dhis2.org/demo",
    "pipeline": [
      {"type": "dhis2", "username": "admin", "password": "district"},
      {"type": "dhis2-version", "username": "admin", "password": "district", "min": "2.38.0"}
    ],
    "tags": ["dhis2", "demo"]
  }'
```

### Run check for a monitor

```bash
curl -X POST http://localhost:8000/api/monitors/{id}/check -u admin:admin
```

### List monitors by tag

```bash
curl http://localhost:8000/api/monitors?tag=critical -u admin:admin
```

### Create monitor with cron schedule

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hourly Check",
    "url": "https://api.example.com/health",
    "pipeline": [{"type": "http"}],
    "schedule": "0 * * * *",
    "tags": ["scheduled"]
  }'
```

## Scheduling

Monitors support two scheduling modes:

### Interval-based (default)
```json
{
  "interval": 30
}
```
Checks run every N seconds (minimum 10).

### Cron-based
```json
{
  "schedule": "*/5 * * * *"
}
```
Uses standard cron syntax: `minute hour day month weekday`

| Schedule | Description |
|----------|-------------|
| `* * * * *` | Every minute |
| `*/5 * * * *` | Every 5 minutes |
| `*/15 * * * *` | Every 15 minutes |
| `0 * * * *` | Every hour |
| `0 */6 * * *` | Every 6 hours |
| `0 9 * * *` | Daily at 9am |
| `0 9 * * 1-5` | Weekdays at 9am |
| `0 0 * * 0` | Weekly on Sunday |

Note: Schedule execution requires an external scheduler (cron, systemd timer, or orchestrator) to call the check endpoint at the specified times.

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `UPTIMER_USERNAME` | admin | API username |
| `UPTIMER_PASSWORD` | admin | API password |
| `UPTIMER_SECRET_KEY` | change-me | Session secret |
| `UPTIMER_HOST` | 127.0.0.1 | Server host |
| `UPTIMER_PORT` | 8000 | Server port |
| `UPTIMER_MONGODB_URI` | mongodb://localhost:27017 | MongoDB URI |
| `UPTIMER_MONGODB_DB` | uptimer | Database name |
| `UPTIMER_RESULTS_RETENTION` | 10000000 | Max results per monitor |

## Development

```bash
make install    # Install dependencies
make lint       # Run ruff + mypy + pyright
make test       # Run tests
make coverage   # Run tests with coverage
make serve      # Start API server
make clean      # Clean temp files
```

## Architecture

```
src/uptimer/
  stages/             # Pluggable stage system
    base.py           # Stage base class, CheckResult, CheckContext
    registry.py       # Stage registration
    http.py           # HTTP stage
    ssl.py            # SSL certificate stage
    tcp.py            # TCP port stage
    dns.py            # DNS resolution stage
    jq.py             # jq expression extractor
    jsonpath.py       # JSONPath extractor
    regex.py          # Regex extractor
    header.py         # Header extractor
    threshold.py      # Threshold assertion
    contains.py       # Content assertion
    age.py            # Timestamp assertion
    json_schema.py    # JSON schema validation
    dhis2.py          # DHIS2 system check
    dhis2_checks.py   # DHIS2 version/integrity/job/analytics
  web/
    api/              # REST API routes
    app.py            # FastAPI app factory
  storage.py          # MongoDB storage layer
  schemas.py          # Pydantic models
  settings.py         # Configuration

clients/web/          # React + Next.js frontend
  src/
    app/              # Next.js pages
    components/       # React components
    lib/              # API client
```

## Adding a Custom Stage

```python
from uptimer.stages.base import Stage, CheckResult, Status, CheckContext
from uptimer.stages.registry import register_stage

@register_stage
class MyStage(Stage):
    name = "my-stage"
    description = "My custom stage"
    is_network_stage = True  # Set False for transformers

    def __init__(self, custom_option: str = "default"):
        self.custom_option = custom_option

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        # Access previous response data via context
        if context and context.response_body:
            body = context.response_body

        # Store values for subsequent stages
        if context:
            context.values["my_value"] = "extracted"

        return CheckResult(
            status=Status.UP,
            url=url,
            message="OK",
            elapsed_ms=0,
            details={"custom": "data"},
        )
```

## License

MIT
