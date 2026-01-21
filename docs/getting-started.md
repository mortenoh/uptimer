# Getting Started

For a conceptual overview of Uptimer's architecture and features, see the [Introduction Guide](introduction.md).

## Quick Start with Docker

The easiest way to run Uptimer is using the pre-built Docker images from GitHub Container Registry:

```bash
# Download the compose file
curl -O https://raw.githubusercontent.com/mortenoh/uptimer/main/compose.ghcr.yml

# Start all services
docker compose -f compose.ghcr.yml up -d
```

This starts MongoDB, the API server, and the frontend. Open http://localhost:3000 and login with `admin` / `admin`.

To stop:

```bash
docker compose -f compose.ghcr.yml down
```

## Local Installation

If you prefer to run locally or want to contribute:

```bash
# Clone the repository
git clone https://github.com/mortenoh/uptimer.git
cd uptimer

# Install with uv
uv sync
```

## Local Quick Start

### 1. Start MongoDB

Uptimer uses MongoDB for storage:

```bash
# Using Docker
docker run -d -p 27017:27017 mongo:7

# Or install locally
brew install mongodb-community  # macOS
```

### 2. Start the Server

```bash
uptimer serve
```

The server runs at `http://localhost:8000` by default.

### 3. Create a Monitor

```bash
# Add a basic HTTP monitor
uptimer add "Google" https://google.com

# Add with multiple checks and tags
uptimer add "My API" https://api.example.com \
  --stage http --stage ssl \
  --tag production --interval 60
```

### 4. Run Checks

```bash
# Check a specific monitor
uptimer check <monitor-id>

# Check all monitors
uptimer check-all

# View check history
uptimer results <monitor-id>
```

### 5. List Monitors

```bash
# List all monitors
uptimer list

# Filter by tag
uptimer list --tag production

# JSON output
uptimer --json list
```

## Configuration

Create a config file:

```bash
uptimer init
```

Edit `config.yaml`:

```yaml
# Authentication
username: admin
password: your-secure-password
secret_key: change-me-in-production

# Server
host: 127.0.0.1
port: 8000

# CLI client
api_url: http://localhost:8000

# MongoDB
mongodb_uri: mongodb://localhost:27017
mongodb_db: uptimer
```

Settings can also be set via environment variables with `UPTIMER_` prefix:

```bash
export UPTIMER_PASSWORD=secret
export UPTIMER_API_URL=http://localhost:8000
```

## Web UI

The React frontend runs separately from the API:

```bash
cd clients/web
npm install
npm run dev
```

Access the dashboard at `http://localhost:3000`. Login with the credentials from your config (default: `admin`/`admin`).

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
