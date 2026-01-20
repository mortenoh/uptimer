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
  - `settings.py` - Pydantic settings from env
  - `logging.py` - Structlog configuration
  - `checkers/` - Pluggable checker system
    - `base.py` - Checker base class, CheckResult, Status enum
    - `http.py` - Default HTTP checker
    - `dhis2.py` - DHIS2 checker with auth
    - `registry.py` - Checker registration
  - `web/` - FastAPI web UI
    - `app.py` - App factory
    - `routes.py` - Web routes and API
    - `templates/` - Jinja2 templates

## Adding new checkers

1. Create new file in `src/uptimer/checkers/`
2. Subclass `Checker`, set `name` and `description`
3. Implement `check(url, verbose) -> CheckResult`
4. Register via `@register_checker` decorator
5. Add tests in `tests/test_checkers.py`

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
