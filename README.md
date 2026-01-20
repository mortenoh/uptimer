# Uptimer

Service uptime monitoring with a modern React dashboard.

## Features

- REST API for monitor management
- Modern React + shadcn/ui dashboard with dark theme
- MongoDB storage for monitors and results
- Pluggable checker system with 15+ check types
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

## Available Checkers

### Network Checks

| Checker | Description | Options |
|---------|-------------|---------|
| `http` | HTTP request with redirect following | `timeout` |
| `ssl` | SSL certificate validity check | `warn_days` (default: 30) |
| `tcp` | TCP port connectivity | `port` |
| `dns` | DNS resolution check | `expected_ip` |

### Value Extractors

| Checker | Description | Options |
|---------|-------------|---------|
| `jq` | Extract from JSON using jq syntax | `expr`, `store_as` |
| `jsonpath` | Extract using JSONPath syntax | `expr`, `store_as` |
| `regex` | Extract using regex capture groups | `pattern`, `store_as` |
| `header` | Extract HTTP response headers | `pattern` (header name), `store_as` |

### Assertions

| Checker | Description | Options |
|---------|-------------|---------|
| `threshold` | Assert value within bounds | `value`, `min`, `max` |
| `contains` | Check response contains text | `pattern`, `negate` |
| `age` | Validate timestamp freshness | `value`, `max_age` |
| `json-schema` | Validate against JSON schema | `schema` |

### DHIS2 Checks

| Checker | Description | Options |
|---------|-------------|---------|
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
    "checks": [{"type": "http"}],
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
    "checks": [
      {"type": "http"},
      {"type": "jq", "expr": ".status", "store_as": "status"},
      {"type": "threshold", "value": "$elapsed_ms", "max": 2000}
    ],
    "tags": ["api", "critical"]
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
    "checks": [
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
  checkers/           # Pluggable checker system
    base.py           # Checker base class
    http.py           # HTTP checker
    ssl.py            # SSL certificate checker
    tcp.py            # TCP port checker
    dns.py            # DNS resolution checker
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

## Adding a Custom Checker

```python
from uptimer.checkers.base import Checker, CheckResult, Status, CheckContext
from uptimer.checkers.registry import register_checker

@register_checker
class MyChecker(Checker):
    name = "my-checker"
    description = "My custom checker"
    is_network_checker = True  # Set False for transformers

    def __init__(self, custom_option: str = "default"):
        self.custom_option = custom_option

    def check(self, url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
        # Access previous response data via context
        if context and context.response_body:
            body = context.response_body

        # Store values for subsequent checks
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
