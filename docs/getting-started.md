# Getting Started

## Installation

```bash
# Clone the repository
git clone https://github.com/mortenoh/uptimer.git
cd uptimer

# Install with uv
uv sync
```

## Basic Usage

### Check a URL

```bash
uptimer check example.com
```

The URL scheme (`https://`) is automatically added if not specified.

### Verbose Mode

Show detailed information including redirects, timing, and headers:

```bash
uptimer check example.com -v
```

### JSON Output

Output structured JSON for metrics collection:

```bash
uptimer --json check example.com
```

## Development

### Run Tests

```bash
make test
```

### Run Linter

```bash
make lint
```

### Build Documentation

```bash
make docs-serve
```
