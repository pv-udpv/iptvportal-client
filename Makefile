.PHONY: help install install-dev sync sync-dev clean test test-cov test-watch lint format type-check check build run cli docs

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)IPTVPortal Client - Development Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install production dependencies only
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	uv sync --no-dev

install-dev: ## Install all dependencies including dev dependencies
	@echo "$(BLUE)Installing all dependencies (including dev)...$(NC)"
	uv sync --dev

sync: ## Sync dependencies (production only)
	@echo "$(BLUE)Syncing production dependencies...$(NC)"
	uv sync --no-dev

sync-dev: ## Sync all dependencies including dev
	@echo "$(BLUE)Syncing all dependencies...$(NC)"
	uv sync --dev

clean: ## Clean up cache files and build artifacts
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	@echo "$(GREEN)Clean complete!$(NC)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	uv run pytest

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	uv run pytest --cov=iptvportal --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	uv run pytest --watch

test-verbose: ## Run tests with verbose output
	@echo "$(BLUE)Running tests (verbose)...$(NC)"
	uv run pytest -v

test-specific: ## Run specific test file (usage: make test-specific TEST=test_file.py)
	@echo "$(BLUE)Running specific test: $(TEST)$(NC)"
	uv run pytest tests/$(TEST) -v

lint: ## Run ruff linter
	@echo "$(BLUE)Running linter...$(NC)"
	uv run ruff check .

lint-fix: ## Run ruff linter with auto-fix
	@echo "$(BLUE)Running linter with auto-fix...$(NC)"
	uv run ruff check --fix .

format: ## Format code with ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	uv run ruff format .

format-check: ## Check code formatting without making changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	uv run ruff format --check .

type-check: ## Run mypy type checker
	@echo "$(BLUE)Running type checker...$(NC)"
	uv run mypy src/iptvportal

check: lint format-check type-check ## Run all checks (lint, format, type)
	@echo "$(GREEN)All checks passed!$(NC)"

check-fix: lint-fix format type-check ## Run all checks with auto-fix
	@echo "$(GREEN)All checks completed with fixes applied!$(NC)"

build: clean ## Build distribution packages
	@echo "$(BLUE)Building package...$(NC)"
	uv build
	@echo "$(GREEN)Build complete! Check dist/ directory.$(NC)"

# CLI shortcuts
cli: ## Run iptvportal CLI (usage: make cli ARGS="command args")
	uv run iptvportal $(ARGS)

cli-help: ## Show CLI help
	uv run iptvportal --help

cli-config: ## Show current configuration
	uv run iptvportal config show

cli-auth: ## Authenticate with IPTVPortal
	uv run iptvportal auth

cli-sync-init: ## Initialize sync database
	uv run iptvportal sync init

cli-sync-pull: ## Pull data from IPTVPortal
	uv run iptvportal sync pull

cli-sync-status: ## Show sync status
	uv run iptvportal sync status

# Development shortcuts
dev: install-dev ## Set up development environment
	@echo "$(GREEN)Development environment ready!$(NC)"

shell: ## Start IPython shell with project context
	@echo "$(BLUE)Starting IPython shell...$(NC)"
	uv run ipython

version: ## Show project version
	@echo "$(BLUE)IPTVPortal Client$(NC)"
	@grep "^version" pyproject.toml | head -1

# Pre-commit style check
pre-commit: check-fix test ## Run all pre-commit checks (format, lint, type, test)
	@echo "$(GREEN)✓ Pre-commit checks passed!$(NC)"

# CI-style check (no fixes, fail on issues)
ci: format-check lint type-check test-cov ## Run all CI checks (no auto-fix)
	@echo "$(GREEN)✓ CI checks passed!$(NC)"

# Quick feedback loop for development
quick: lint-fix test ## Quick check: fix lint and run tests
	@echo "$(GREEN)✓ Quick check complete!$(NC)"

# Documentation helpers
docs-serve: ## Serve documentation locally (if docs server exists)
	@echo "$(YELLOW)Documentation serving not yet implemented$(NC)"
	@echo "View docs in docs/ directory"

# Database/Cache management
cache-clear: ## Clear all caches
	@echo "$(YELLOW)Clearing caches...$(NC)"
	rm -rf .cache/
	uv run iptvportal cache clear 2>/dev/null || echo "No cache to clear"
	@echo "$(GREEN)Cache cleared!$(NC)"

# Show project info
info: ## Show project information
	@echo "$(BLUE)Project Information$(NC)"
	@echo "===================="
	@echo "Name:         iptvportal-client"
	@echo "Version:      $$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)"
	@echo "Python:       >= 3.12"
	@echo "Package Tool: uv"
	@echo ""
	@echo "$(BLUE)Available Commands:$(NC)"
	@make help

# Install pre-commit hooks (optional)
install-hooks: ## Install git pre-commit hooks
	@echo "$(BLUE)Installing git hooks...$(NC)"
	@echo "#!/bin/sh" > .git/hooks/pre-commit
	@echo "make pre-commit" >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "$(GREEN)Git hooks installed!$(NC)"
