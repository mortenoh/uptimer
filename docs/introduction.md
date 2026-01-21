# Introduction to Uptimer

This guide takes you from zero knowledge to understanding the core concepts of Uptimer and running your first monitors.

## What is Uptimer?

Uptimer is a **service uptime monitoring tool**. It helps you answer questions like:

- Is my website responding?
- Is my API returning valid data?
- Is my SSL certificate about to expire?
- Is my database connection healthy?
- Are my scheduled jobs running on time?

You define **monitors** that periodically check your services and store the results. When something goes wrong, you can see it immediately in the dashboard or query the API.

## Core Concepts

### Monitors

A **monitor** represents a single service you want to check. Each monitor has:

- **Name**: Human-readable identifier (e.g., "Production API")
- **URL**: The endpoint to check (e.g., `https://api.example.com/health`)
- **Pipeline**: One or more stages that define what checks to perform
- **Interval**: How often to run checks (in seconds)
- **Tags**: Labels for organizing monitors (e.g., "production", "critical")

### Stages

A **stage** is a single check or transformation in a pipeline. Uptimer includes 15+ built-in stages:

| Category | Stages | Purpose |
|----------|--------|---------|
| **Network** | `http`, `ssl`, `tcp`, `dns` | Check connectivity and certificates |
| **Extractors** | `jq`, `jsonpath`, `regex`, `header` | Pull values from responses |
| **Assertions** | `threshold`, `contains`, `age`, `json-schema` | Validate extracted values |
| **DHIS2** | `dhis2`, `dhis2-version`, `dhis2-integrity` | Health information system checks |

### Pipelines

A **pipeline** is a sequence of stages that run in order. Each stage can:

1. Access the HTTP response from previous network stages
2. Extract values and store them for later stages
3. Make assertions that determine the final status

Example pipeline flow:
```
http → jq (extract value) → threshold (assert value in range)
```

### Check Results

When a monitor runs, it produces a **check result** with:

- **Status**: `up`, `degraded`, or `down`
- **Message**: Human-readable summary
- **Elapsed time**: How long the check took
- **Details**: Stage-specific data (status codes, extracted values, etc.)

### Status Levels

| Status | Meaning | Example |
|--------|---------|---------|
| **UP** | All checks passed | HTTP returned 200, SSL valid |
| **DEGRADED** | Warnings present | SSL expires in 20 days |
| **DOWN** | Check failed | Connection refused, 500 error |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CLI       │────▶│  REST API   │────▶│  MongoDB    │
│  (client)   │     │  (FastAPI)  │     │  (storage)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   ▲
                    ┌──────┴──────┐            │
                    │   React     │      ┌─────┴─────┐
                    │  Frontend   │      │ Scheduler │
                    └─────────────┘      └───────────┘
```

- **CLI**: Command-line client that talks to the API
- **REST API**: Manages monitors, runs checks, stores results
- **MongoDB**: Persists monitors, check history, and scheduler jobs
- **Scheduler**: Background process that runs checks automatically
- **React Frontend**: Visual dashboard at `http://localhost:3000`

## Built-in Scheduler

Uptimer includes a **built-in scheduler** that automatically runs checks. When you start the server with `uptimer serve`, the scheduler:

1. Loads all enabled monitors from MongoDB
2. Creates a job for each monitor based on its `interval` or `schedule`
3. Runs checks in the background and stores results
4. Updates automatically when monitors are created, updated, or deleted

**Interval-based scheduling** (default):
```json
{"interval": 30}
```
Runs every 30 seconds.

**Cron-based scheduling**:
```json
{"schedule": "*/5 * * * *"}
```
Runs every 5 minutes using cron syntax.

The scheduler uses MongoDB to persist job state, so schedules survive server restarts.

## Your First Monitor

Let's create a monitor step by step using [JSONPlaceholder](https://jsonplaceholder.typicode.com), a free fake API for testing.

### 1. Start the Services

```bash
# Start MongoDB
docker run -d -p 27017:27017 mongo:7

# Start the API server
uptimer serve

# (Optional) Start the React frontend
cd clients/web && npm install && npm run dev
```

### 2. Create a Simple HTTP Monitor

Monitor the JSONPlaceholder users endpoint:

```bash
uptimer add "JSONPlaceholder Users" https://jsonplaceholder.typicode.com/users
```

Output:
```
Created monitor: JSONPlaceholder Users (id: abc123...)
```

This creates a monitor with the default `http` stage that checks if the URL returns a successful response.

### 3. Run a Check

```bash
uptimer check abc123
```

Output:
```
Status: UP
Message: http: 200 OK
Elapsed: 245ms
```

### 4. View Your Monitors

```bash
uptimer list
```

Output:
```
ID        NAME                    URL                                        STATUS  LAST CHECK
abc123    JSONPlaceholder Users   jsonplaceholder.typicode.com/users         up      2 minutes ago
```

### 5. View Check History

```bash
uptimer results abc123
```

Shows the history of all checks for this monitor.

## Building Pipelines

The real power of Uptimer comes from chaining stages together. Let's build progressively more sophisticated monitors.

### Example 1: HTTP + Response Validation

Check that the API returns valid JSON with expected content:

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "JSONPlaceholder Posts",
    "url": "https://jsonplaceholder.typicode.com/posts",
    "pipeline": [
      {"type": "http"},
      {"type": "contains", "pattern": "userId"}
    ],
    "tags": ["api", "demo"]
  }'
```

This pipeline:
1. `http` - Fetches the URL
2. `contains` - Verifies the response contains "userId"

### Example 2: Extract and Validate a Value

Check that we get exactly 100 posts:

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Posts Count Check",
    "url": "https://jsonplaceholder.typicode.com/posts",
    "pipeline": [
      {"type": "http"},
      {"type": "jq", "expr": "length", "store_as": "post_count"},
      {"type": "threshold", "value": "$post_count", "min": 100, "max": 100}
    ],
    "tags": ["api", "demo"]
  }'
```

This pipeline:
1. `http` - Fetches the posts array
2. `jq` - Extracts the array length, stores it as `post_count`
3. `threshold` - Asserts `post_count` equals 100

### Example 3: Validate Response Time

Ensure the API responds within 2 seconds:

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Response Time",
    "url": "https://jsonplaceholder.typicode.com/posts/1",
    "pipeline": [
      {"type": "http"},
      {"type": "threshold", "value": "$elapsed_ms", "max": 2000}
    ],
    "tags": ["api", "performance"]
  }'
```

The special variable `$elapsed_ms` contains the HTTP request duration.

### Example 4: Validate JSON Structure

Ensure the response matches a JSON schema:

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Schema Validation",
    "url": "https://jsonplaceholder.typicode.com/users/1",
    "pipeline": [
      {"type": "http"},
      {"type": "json-schema", "schema": {
        "type": "object",
        "required": ["id", "name", "email"],
        "properties": {
          "id": {"type": "integer"},
          "name": {"type": "string"},
          "email": {"type": "string", "format": "email"}
        }
      }}
    ],
    "tags": ["api", "schema"]
  }'
```

### Example 5: Extract Nested Values with JSONPath

Extract and validate a specific field:

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Company Check",
    "url": "https://jsonplaceholder.typicode.com/users/1",
    "pipeline": [
      {"type": "http"},
      {"type": "jsonpath", "expr": "$.company.name", "store_as": "company"},
      {"type": "contains", "pattern": "Romaguera"}
    ],
    "tags": ["api", "demo"]
  }'
```

### Example 6: SSL Certificate Monitoring

Monitor SSL certificate expiration (warns 30 days before expiry):

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "JSONPlaceholder SSL",
    "url": "https://jsonplaceholder.typicode.com",
    "pipeline": [
      {"type": "http"},
      {"type": "ssl", "warn_days": 30}
    ],
    "tags": ["ssl", "demo"]
  }'
```

### Example 7: Complete Health Check Pipeline

A production-ready health check combining multiple validations:

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Full API Health Check",
    "url": "https://jsonplaceholder.typicode.com/posts/1",
    "pipeline": [
      {"type": "http"},
      {"type": "ssl", "warn_days": 14},
      {"type": "threshold", "value": "$elapsed_ms", "max": 3000},
      {"type": "jq", "expr": ".id", "store_as": "post_id"},
      {"type": "threshold", "value": "$post_id", "min": 1, "max": 100}
    ],
    "interval": 60,
    "tags": ["production", "critical"]
  }'
```

This comprehensive check:
1. Verifies HTTP connectivity
2. Checks SSL certificate validity
3. Ensures response time under 3 seconds
4. Extracts the post ID
5. Validates the ID is in expected range

## Using Tags

Tags help organize monitors. You can filter by tag in both CLI and API:

```bash
# List only production monitors
uptimer list --tag production

# Check all critical monitors
uptimer check-all --tag critical

# API: List monitors by tag
curl "http://localhost:8000/api/monitors?tag=production" -u admin:admin
```

## CLI Quick Reference

| Command | Description |
|---------|-------------|
| `uptimer add NAME URL` | Create a monitor |
| `uptimer list` | List all monitors |
| `uptimer list --tag TAG` | List monitors with tag |
| `uptimer get ID` | Get monitor details |
| `uptimer check ID` | Run check now |
| `uptimer check-all` | Check all monitors |
| `uptimer results ID` | View check history |
| `uptimer delete ID` | Delete a monitor |
| `uptimer tags` | List all tags |
| `uptimer stages` | List available stages |
| `uptimer --json COMMAND` | Output as JSON |

## Next Steps

- [CLI Reference](cli-reference.md) - Full CLI documentation
- [REST API](rest-api.md) - API endpoints and examples
- [Stages Reference](stages/index.md) - All available stages
- [Custom Stages](stages/custom.md) - Build your own stages
