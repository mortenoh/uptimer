# REST API

All API endpoints require authentication via session cookie. First login via `POST /login`.

## Monitors

### List Monitors

```
GET /api/monitors
GET /api/monitors?tag=production
```

Response: `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "Google",
    "url": "https://www.google.com",
    "checks": [{"type": "http"}],
    "interval": 30,
    "schedule": null,
    "enabled": true,
    "tags": ["search", "public"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "last_check": "2024-01-01T12:00:00Z",
    "last_status": "up"
  }
]
```

### Create Monitor

```
POST /api/monitors
```

Request body:
```json
{
  "name": "My Service",
  "url": "https://api.example.com",
  "checks": [
    {"type": "http"},
    {"type": "dhis2", "username": "admin", "password": "district"}
  ],
  "interval": 30,
  "schedule": "*/5 * * * *",
  "enabled": true,
  "tags": ["production", "api"]
}
```

Response: `201 Created`

### Get Monitor

```
GET /api/monitors/{id}
```

Response: `200 OK` or `404 Not Found`

### Update Monitor

```
PUT /api/monitors/{id}
```

Request body (all fields optional):
```json
{
  "name": "Updated Name",
  "checks": [{"type": "http"}],
  "interval": 60,
  "enabled": false,
  "tags": ["staging"]
}
```

Response: `200 OK` or `404 Not Found`

### Delete Monitor

```
DELETE /api/monitors/{id}
```

Response: `204 No Content` or `404 Not Found`

### Run Check

Run all configured checks for a monitor immediately.

```
POST /api/monitors/{id}/check
```

Response: `200 OK`
```json
{
  "id": "result-uuid",
  "monitor_id": "monitor-uuid",
  "status": "up",
  "message": "http: 200 OK; dhis2: 2.41.0",
  "elapsed_ms": 450.5,
  "details": {
    "http": {"status_code": 200},
    "dhis2": {"version": "2.41.0", "revision": "abc123"}
  },
  "checked_at": "2024-01-01T12:00:00Z"
}
```

### Check All Monitors

Run checks for all enabled monitors (optionally filtered by tag).

```
POST /api/monitors/check-all
POST /api/monitors/check-all?tag=production
```

Response: `200 OK` with array of check results.

### Get Results

Get historical check results for a monitor.

```
GET /api/monitors/{id}/results
GET /api/monitors/{id}/results?limit=50
```

Response: `200 OK`
```json
[
  {
    "id": "result-uuid",
    "monitor_id": "monitor-uuid",
    "status": "up",
    "message": "http: 200 OK",
    "elapsed_ms": 150.0,
    "details": {"http": {"status_code": 200}},
    "checked_at": "2024-01-01T12:00:00Z"
  }
]
```

## Tags

### List Tags

Get all unique tags across monitors.

```
GET /api/monitors/tags
```

Response: `200 OK`
```json
["api", "production", "staging"]
```

## Check Types

### HTTP Check

Basic HTTP/HTTPS connectivity check.

```json
{"type": "http"}
```

### DHIS2 Check

DHIS2 instance check with authentication and version info.

```json
{
  "type": "dhis2",
  "username": "admin",
  "password": "district"
}
```

Returns system info including version, revision, build time.

## Status Values

- `up` - All checks passed
- `degraded` - Some issues but service reachable
- `down` - Service unreachable or check failed
