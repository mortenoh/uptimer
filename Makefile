.PHONY: help install lint test test-integration test-all test-performance coverage serve run run-all run-ghcr dev stop logs seed clean docs docs-serve docs-build frontend frontend-build frontend-install docker-build rebuild

# ==============================================================================
# Variables
# ==============================================================================

UV := $(shell command -v uv 2> /dev/null)
VENV_DIR?=.venv
PYTHON := $(VENV_DIR)/bin/python
N?=0

# ==============================================================================
# Help
# ==============================================================================

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@echo "  install          Install Python dependencies"
	@echo "  lint             Run linter and type checker"
	@echo "  test             Run unit tests"
	@echo "  test-integration Run integration tests (require network)"
	@echo "  test-all         Run all tests"
	@echo "  test-performance Show 20 slowest tests"
	@echo "  coverage         Run tests with coverage reporting"
	@echo ""
	@echo "Running:"
	@echo "  run              Docker: MongoDB + API only (no frontend)"
	@echo "  run-all          Docker: Full stack with seeding"
	@echo "  run-ghcr         Docker: Full stack using pre-built ghcr.io images"
	@echo "  dev              Local: Start MongoDB in Docker, print instructions"
	@echo "  serve            Start API dev server with reload"
	@echo "  frontend         Start frontend dev server"
	@echo "  stop             Stop all Docker services"
	@echo "  logs             Follow docker compose logs"
	@echo "  seed             Seed MongoDB with sample monitors"
	@echo ""
	@echo "Building:"
	@echo "  docker-build     Build all Docker images"
	@echo "  rebuild          Force rebuild Docker images (no cache)"
	@echo "  frontend-build   Build frontend for production"
	@echo "  frontend-install Install frontend dependencies"
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
	@echo ">>> Installing Python dependencies"
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
	@echo ">>> Starting MongoDB + API"
	@docker compose down
	@docker compose build api
	@docker compose up -d mongo api
	@echo ">>> Waiting for API to be healthy..."
	@docker compose --profile seed up seed
	@echo ">>> API: http://localhost:8000"
	@docker compose logs -f mongo api

run-all:
	@echo ">>> Starting all services"
	@docker compose down
	@docker compose build
	@docker compose up -d
	@echo ">>> Waiting for API to be healthy..."
	@docker compose --profile seed up seed
	@echo ">>> API: http://localhost:8000 | Frontend: http://localhost:3000"
	@docker compose logs -f

run-ghcr:
	@echo ">>> Starting all services using pre-built ghcr.io images"
	@docker compose -f compose.ghcr.yml pull
	@docker compose -f compose.ghcr.yml up -d
	@echo ">>> API: http://localhost:8000 | Frontend: http://localhost:3000"
	@docker compose -f compose.ghcr.yml logs -f

dev:
	@echo ">>> Starting MongoDB in Docker, API and frontend locally"
	@docker compose up -d mongo
	@echo ">>> Waiting for MongoDB..."
	@sleep 2
	@$(MAKE) seed
	@echo ""
	@echo ">>> MongoDB running at localhost:27017"
	@echo ">>> Start API: make serve"
	@echo ">>> Start frontend: make frontend"

serve:
	@$(UV) run uptimer serve --reload

frontend:
	@echo ">>> Starting frontend dev server on http://localhost:3001"
	@cd clients/web && npm install
	@cd clients/web && npm run dev -- -p 3001

frontend-install:
	@echo ">>> Installing frontend dependencies"
	@cd clients/web && npm install

frontend-build:
	@echo ">>> Building frontend for production"
	@cd clients/web && npm install
	@cd clients/web && npm run build

stop:
	@echo ">>> Stopping services"
	@docker compose down

logs:
	@docker compose logs -f

seed:
	@echo ">>> Seeding MongoDB with sample monitors"
	@N=$(N) $(UV) run python scripts/seed_data.py

# ==============================================================================
# Building
# ==============================================================================

docker-build:
	@echo ">>> Building Docker images"
	@docker compose build

rebuild:
	@echo ">>> Force rebuilding Docker images (no cache)"
	@docker compose build --no-cache

# ==============================================================================
# Documentation
# ==============================================================================

docs-serve:
	@echo ">>> Serving documentation at http://127.0.0.1:8001"
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
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .coverage htmlcov coverage.xml
	@rm -rf .pyright
	@rm -rf dist build *.egg-info
	@rm -rf site

# ==============================================================================
# Default
# ==============================================================================

.DEFAULT_GOAL := help
