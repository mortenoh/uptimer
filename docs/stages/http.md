# HTTP Stage

The HTTP stage performs GET requests and follows redirects.

## Configuration

```json
{
  "type": "http"
}
```

### With custom headers

```json
{
  "type": "http",
  "headers": {
    "Authorization": "Bearer your-token",
    "X-API-Key": "your-api-key",
    "Accept": "application/json"
  }
}
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `headers` | object | `{}` | Custom HTTP headers to send |
| `timeout` | float | `10.0` | Request timeout in seconds |

## Behavior

1. Adds `https://` if no protocol specified
2. Follows redirects (up to httpx default limit)
3. Sends custom headers merged with default User-Agent
4. Returns final response status

## Status Mapping

| HTTP Status | Check Status |
|-------------|--------------|
| 1xx-3xx | UP |
| 4xx-5xx | DEGRADED |
| Connection error | DOWN |

## Details

The HTTP stage provides these details:

| Key | Description |
|-----|-------------|
| `status_code` | HTTP response status code |
| `http_version` | HTTP version (e.g., HTTP/1.1) |
| `final_url` | Final URL after redirects |
| `server` | Server header value |
| `content_type` | Content-Type header value |
| `redirects` | List of redirect hops |

## Examples

### Basic HTTP monitor

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google",
    "url": "https://google.com",
    "pipeline": [{"type": "http"}]
  }'
```

### With API authentication

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Protected API",
    "url": "https://api.example.com/health",
    "pipeline": [{
      "type": "http",
      "headers": {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIs...",
        "X-API-Key": "your-api-key"
      }
    }]
  }'
```

### Check result example

```json
{
  "status": "up",
  "message": "200",
  "elapsed_ms": 145.5,
  "details": {
    "status_code": 200,
    "http_version": "HTTP/1.1",
    "final_url": "https://www.google.com/",
    "server": "gws",
    "content_type": "text/html; charset=ISO-8859-1",
    "redirects": [{"status": 301, "location": "https://www.google.com/"}]
  }
}
```
