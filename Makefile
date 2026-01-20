.PHONY: help install lint test test-integration test-all test-performance coverage serve run run-local stop logs seed clean docs docs-serve docs-build

# ==============================================================================
# Variables
# ==============================================================================

UV := $(shell command -v uv 2> /dev/null)
VENV_DIR?=.venv
PYTHON := $(VENV_DIR)/bin/python

# ==============================================================================
# Help
# ==============================================================================

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@echo "  install          Install dependencies"
	@echo "  lint             Run linter and type checker"
	@echo "  test             Run unit tests"
	@echo "  test-integration Run integration tests (require network)"
	@echo "  test-all         Run all tests"
	@echo "  test-performance Show 20 slowest tests"
	@echo "  coverage         Run tests with coverage reporting"
	@echo ""
	@echo "Running:"
	@echo "  run              Clean start with docker compose + seed data"
	@echo "  run-local        Start server locally (requires local MongoDB)"
	@echo "  serve            Start dev server with reload"
	@echo "  stop             Stop docker compose services"
	@echo "  logs             Follow docker compose logs"
	@echo "  seed             Seed MongoDB with sample monitors"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Serve documentation locally"
	@echo "  docs-build       Build documentation site"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean            Clean up temporary files and containers"

# ==============================================================================
# Development
# ==============================================================================

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
	@echo ">>> Running unit tests"
	@$(UV) run pytest -q -m "not integration"

test-integration:
	@echo ">>> Running integration tests"
	@$(UV) run pytest -q -m integration

test-all:
	@echo ">>> Running all tests"
	@$(UV) run pytest -q

test-performance:
	@echo ">>> Running tests and showing 20 slowest"
	@$(UV) run pytest -v --durations=20

coverage:
	@echo ">>> Running tests with coverage"
	@$(UV) run coverage run -m pytest -q -m "not integration"
	@$(UV) run coverage report
	@$(UV) run coverage xml

# ==============================================================================
# Running
# ==============================================================================

run:
	@echo ">>> Stopping and cleaning up containers"
	@docker compose down -v
	@echo ">>> Building fresh images"
	@docker compose build --no-cache
	@echo ">>> Starting services"
	@docker compose up -d --remove-orphans
	@echo ">>> Waiting for services to be ready..."
	@sleep 3
	@echo ">>> Seeding database"
	@$(UV) run python scripts/seed_data.py
	@echo ">>> Done! App running at http://localhost:8000"
	@echo ">>> Use 'make logs' to follow logs"

run-local:
	@echo ">>> Starting server locally (requires MongoDB at localhost:27017)"
	@$(UV) run uptimer serve

serve:
	@$(UV) run uptimer serve --reload

stop:
	@echo ">>> Stopping services"
	@docker compose down

logs:
	@docker compose logs -f

seed:
	@echo ">>> Seeding MongoDB with sample monitors"
	@$(UV) run python scripts/seed_data.py

# ==============================================================================
# Documentation
# ==============================================================================

docs-serve:
	@echo ">>> Serving documentation at http://127.0.0.1:8000"
	@$(UV) run --group docs mkdocs serve

docs-build:
	@echo ">>> Building documentation site"
	@$(UV) run --group docs mkdocs build

docs: docs-serve

# ==============================================================================
# Cleanup
# ==============================================================================

clean:
	@echo ">>> Stopping containers"
	@docker compose down -v 2>/dev/null || true
	@echo ">>> Cleaning up files"
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
