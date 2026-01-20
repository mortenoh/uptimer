.PHONY: help install lint test test-durations coverage clean

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

# ==============================================================================
# Default
# ==============================================================================

.DEFAULT_GOAL := help
