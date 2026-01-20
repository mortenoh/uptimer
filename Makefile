.PHONY: help install lint test test-durations coverage clean docs docs-serve docs-build serve

# ==============================================================================
# Venv
# ==============================================================================

UV := $(shell command -v uv 2> /dev/null)
VENV_DIR?=.venv
PYTHON := $(VENV_DIR)/bin/python

# ==============================================================================
# Targets
# ==============================================================================

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install        Install dependencies"
	@echo "  lint           Run linter and type checker"
	@echo "  test           Run tests"
	@echo "  test-durations Show 20 slowest tests"
	@echo "  coverage       Run tests with coverage reporting"
	@echo "  serve          Start web UI server"
	@echo "  docs-serve     Serve documentation locally"
	@echo "  docs-build     Build documentation site"
	@echo "  docs           Alias for docs-serve"
	@echo "  clean          Clean up temporary files"

install:
	@echo ">>> Installing dependencies"
	@$(UV) sync

lint:
	@echo ">>> Running linter"
	@$(UV) run ruff format .
	@$(UV) run ruff check . --fix
	@echo ">>> Running type checker"
	@$(UV) run mypy src
	@$(UV) run pyright

test:
	@echo ">>> Running tests"
	@$(UV) run pytest -q

test-durations:
	@echo ">>> Running tests and showing 20 slowest"
	@$(UV) run pytest -q --durations=20

coverage:
	@echo ">>> Running tests with coverage"
	@$(UV) run coverage run -m pytest -q
	@$(UV) run coverage report
	@$(UV) run coverage xml

serve:
	@$(UV) run uptimer serve --reload

docs-serve:
	@echo ">>> Serving documentation at http://127.0.0.1:8000"
	@$(UV) run --group docs mkdocs serve

docs-build:
	@echo ">>> Building documentation site"
	@$(UV) run --group docs mkdocs build

docs: docs-serve

clean:
	@echo ">>> Cleaning up"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .coverage htmlcov coverage.xml
	@rm -rf .pyright
	@rm -rf dist build *.egg-info
	@rm -rf site

# ==============================================================================
# Default
# ==============================================================================

.DEFAULT_GOAL := help
