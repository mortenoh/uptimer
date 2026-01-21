# Stages

Uptimer uses a pluggable stage system. Each stage performs a specific check, extraction, or assertion within a pipeline.

## Available Stages

| Name | Category | Description |
|------|----------|-------------|
| `http` | Network | HTTP request with redirect following |
| `ssl` | Network | SSL certificate validity check |
| `tcp` | Network | TCP port connectivity |
| `dns` | Network | DNS resolution check |
| `jq` | Extractor | Extract values using jq syntax |
| `jsonpath` | Extractor | Extract values using JSONPath |
| `regex` | Extractor | Extract values using regex |
| `header` | Extractor | Extract HTTP response headers |
| `threshold` | Assertion | Assert value within bounds |
| `contains` | Assertion | Check response contains text |
| `age` | Assertion | Validate timestamp freshness |
| `json-schema` | Assertion | Validate against JSON schema |
| `dhis2` | DHIS2 | System info check |

## Using Stages

Stages are configured in the `pipeline` array when creating a monitor:

```bash
curl -X POST http://localhost:8000/api/monitors \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API",
    "url": "https://api.example.com/health",
    "pipeline": [
      {"type": "http"},
      {"type": "jq", "expr": ".status", "store_as": "status"},
      {"type": "threshold", "value": "$elapsed_ms", "max": 2000}
    ]
  }'
```

List all available stages:

```bash
uptimer stages
```

## Stage Output

All stages return a `CheckResult` with:

- `status` - UP, DEGRADED, or DOWN
- `url` - The checked URL
- `message` - Status message
- `elapsed_ms` - Time taken in milliseconds
- `details` - Stage-specific details

## Pipeline Context

Stages in a pipeline share a `CheckContext` that contains:

- `response_body` - HTTP response body from network stages
- `response_headers` - HTTP response headers
- `values` - Dictionary of extracted values (use `store_as` to add)

Access stored values in later stages using `$variable_name` syntax:

```json
{"type": "threshold", "value": "$my_extracted_value", "max": 100}
```

Built-in values:
- `$elapsed_ms` - HTTP request duration in milliseconds
