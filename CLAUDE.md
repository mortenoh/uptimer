# Claude Code Preferences

## Commit and PR Guidelines

- No attribution (Co-Authored-By) in commits or PRs
- No emojis anywhere
- Use conventional commits format: feat:, fix:, docs:, refactor:, test:, chore:
- Use conventional branch naming: feat/, fix/, docs/, refactor/, test/, chore/

## Code Style

- Follow ruff and mypy/pyright configurations in pyproject.toml
- Line length: 120 characters
- Google-style docstrings
- Use typer for CLI, rich for output formatting
- Keep CLI output concise by default, verbose with -v flag

## Testing

- Always add tests for new features
- Tests go in `tests/` directory
- Use pytest with typer.testing.CliRunner for CLI tests
- Run `make test` before committing
- Run `make test-performance` to check for slow tests
- Aim for good coverage on core functionality

## Architecture

- `src/uptimer/` - Main package
  - `cli.py` - Typer CLI entry point
  - `main.py` - Entry point for `uptimer` command
  - `settings.py` - Pydantic settings from env/YAML
  - `logging.py` - Structlog configuration
  - `schemas.py` - Pydantic models for Monitor, Stage, CheckResult
  - `storage.py` - MongoDB storage layer
  - `pipeline.py` - Shared pipeline execution utilities
  - `scheduler.py` - APScheduler background job scheduler
  - `stages/` - Pluggable stage system (17 stages total)
    - `base.py` - Stage base class, CheckResult, Status enum, CheckContext
    - `registry.py` - Stage registration with @register_stage decorator
    - Network stages: `http.py`, `ssl.py`, `dns.py`, `tcp.py`
    - DHIS2 stages: `dhis2.py`, `dhis2_checks.py` (version, integrity, job, analytics)
    - Extractors: `jq.py`, `jsonpath.py`, `regex.py`, `header.py`
    - Validators: `threshold.py`, `contains.py`, `age.py`, `json_schema.py`
  - `web/` - FastAPI web UI
    - `app.py` - App factory with CORS, session middleware
    - `routes.py` - Web routes (login, health endpoint)
    - `api/` - REST API routes
      - `monitors.py` - Monitor CRUD and check endpoints
      - `stages.py` - Stage metadata endpoint
      - `deps.py` - Dependency injection (storage, auth)
- `clients/web/` - Next.js frontend
- `scripts/` - Utility scripts (seed_data.py)

## Adding new stages

1. Create new file in `src/uptimer/stages/`
2. Subclass `Stage`, set `name` and `description`
3. Implement `check(url, verbose) -> CheckResult`
4. Register via `@register_stage` decorator
5. Add tests in `tests/test_stages.py`

## Makefile targets

- `make install` - Install dependencies
- `make lint` - Run ruff + mypy + pyright
- `make test` - Run tests
- `make test-performance` - Show slowest tests
- `make coverage` - Run with coverage
- `make serve` - Start web UI
- `make docker-build` - Build Docker image
- `make docker-run` - Run Docker container
- `make docs` - Serve documentation
