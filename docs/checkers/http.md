# HTTP Checker

The default HTTP checker performs GET requests and follows redirects.

## Usage

```bash
uptimer check example.com
uptimer check example.com -c http
```

## Behavior

1. Adds `https://` if no protocol specified
2. Follows redirects (up to httpx default limit)
3. Returns final response status

## Status Mapping

| HTTP Status | Check Status |
|-------------|--------------|
| 1xx-3xx | UP |
| 4xx-5xx | DEGRADED |
| Connection error | DOWN |

## Details

The HTTP checker provides these details:

| Key | Description |
|-----|-------------|
| `status_code` | HTTP response status code |
| `http_version` | HTTP version (e.g., HTTP/1.1) |
| `final_url` | Final URL after redirects |
| `server` | Server header value |
| `content_type` | Content-Type header value |
| `redirects` | List of redirect hops |

## Example Output

### Console (verbose)

```
UP https://google.com (200)
  Redirects:
    301 -> https://www.google.com/
  Final URL: https://www.google.com/
  Time: 1030ms
  HTTP: HTTP/1.1
  Server: gws
  Content-Type: text/html; charset=ISO-8859-1
```

### JSON

```json
{
  "status": "up",
  "url": "https://google.com",
  "message": "200",
  "elapsed_ms": 934.67,
  "status_code": 200,
  "http_version": "HTTP/1.1",
  "final_url": "https://www.google.com/",
  "server": "gws",
  "content_type": "text/html; charset=ISO-8859-1",
  "redirects": [{"status": 301, "location": "https://www.google.com/"}]
}
```
