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

## Architecture

- `src/uptimer/` - Main package
  - `cli.py` - Typer CLI entry point
  - `main.py` - Entry point for `uptimer` command
  - `checkers/` - Pluggable checker system
    - `base.py` - Checker base class, CheckResult, Status enum
    - `http.py` - Default HTTP checker
    - `registry.py` - Checker registration

## Adding new checkers

1. Create new file in `src/uptimer/checkers/`
2. Subclass `Checker`, set `name` and `description`
3. Implement `check(url, verbose) -> CheckResult`
4. Register via `@register_checker` decorator

## Planned features

- DHIS2 checker with username/password auth
- Multiple URL batch checking
- Config file for saved checks
- Web UI with authentication
