# Gmail Calendar Sync - Development Makefile
# Simplifies common development tasks

.PHONY: help install test test-watch lint format type-check quality clean dev debug build run-docker setup performance

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Development Environment
# ============================================================================

install:  ## Install dependencies
	uv sync --all-extras

setup:  ## Setup development environment (install + pre-commit)
	uv sync --all-extras
	uv run pre-commit install
	@echo "✅ Development environment ready!"

clean:  ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/
	rm -rf dist/ build/ *.egg-info/
	@echo "🧹 Cleaned up generated files"

# ============================================================================
# Code Quality
# ============================================================================

test:  ## Run tests with coverage
	uv run pytest tests/ -v --cov=src --cov-report=term-missing

test-watch:  ## Run tests in watch mode
	uv run pytest-watch tests/ -- -v --tb=short

test-fast:  ## Run tests without coverage (faster)
	uv run pytest tests/ -v --tb=short

performance:  ## Run performance benchmarks
	uv run pytest tests/test_performance.py -v --benchmark-only --benchmark-sort=mean

lint:  ## Run linting
	uv run ruff check src/ tests/

format:  ## Format code
	uv run ruff format src/ tests/

type-check:  ## Run type checking
	uv run mypy src/

quality: lint format type-check test  ## Run all quality checks
	@echo "✅ All quality checks passed!"

# ============================================================================
# Development & Debugging
# ============================================================================

dev:  ## Run in development mode (recent emails only)
	LOG_LEVEL=DEBUG SYNC_PERIOD_HOURS=1 uv run python src/main.py

debug:  ## Debug mode with detailed logging
	LOG_LEVEL=DEBUG SYNC_PERIOD_HOURS=1 uv run python src/main.py

dev-last3h:  ## Run with last 3 hours of emails
	LOG_LEVEL=DEBUG SYNC_PERIOD_HOURS=3 uv run python src/main.py

dev-today:  ## Run with today's emails only
	LOG_LEVEL=DEBUG SYNC_PERIOD_HOURS=24 uv run python src/main.py

dev-no-slack:  ## Run without Slack notifications
	unset SLACK_WEBHOOK_URL && LOG_LEVEL=DEBUG SYNC_PERIOD_HOURS=1 uv run python src/main.py

# ============================================================================
# Testing & Cleanup
# ============================================================================

test-cleanup:  ## Clean test environment (remove labels/events)
	@echo "⚠️  WARNING: This will remove processed labels and calendar events!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read
	uv run python cleanup_for_test.py
	@echo "🧹 Test environment cleaned"

test-production:  ## Test with production-like settings
	SYNC_PERIOD_HOURS=8 LOG_LEVEL=INFO uv run python src/main.py

# ============================================================================
# Docker & Deployment
# ============================================================================

build:  ## Build Docker image
	docker build -t gmail-calendar-sync:latest .

run-docker:  ## Run Docker container locally
	docker run --env-file .env gmail-calendar-sync:latest

# ============================================================================
# Maintenance
# ============================================================================

update-deps:  ## Update dependencies
	uv sync --upgrade
	uv run pre-commit autoupdate

check-security:  ## Run security checks
	uv run bandit -r src/
	uv run safety check

profile:  ## Profile application performance
	LOG_LEVEL=DEBUG SYNC_PERIOD_HOURS=1 uv run python -m cProfile -o profile.stats src/main.py
	uv run python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

memory-profile:  ## Profile memory usage
	LOG_LEVEL=DEBUG SYNC_PERIOD_HOURS=1 uv run python -m memory_profiler src/main.py

# ============================================================================
# CI/CD Simulation
# ============================================================================

ci-test:  ## Simulate CI testing environment
	uv run pytest tests/ -v --cov=src --cov-report=xml --cov-report=term-missing
	uv run mypy src/
	uv run ruff check src/ tests/
	uv run ruff format src/ tests/ --check

pre-commit-all:  ## Run pre-commit on all files
	uv run pre-commit run --all-files

# ============================================================================
# Development Info
# ============================================================================

info:  ## Show development environment info
	@echo "=== Gmail Calendar Sync Development Environment ==="
	@echo "Python version: $$(python --version)"
	@echo "UV version: $$(uv --version)"
	@echo "Virtual env: $$(which python)"
	@echo "Project dependencies:"
	@uv pip list | head -10
	@echo "..."
	@echo "Total packages: $$(uv pip list | wc -l)"

status:  ## Show git and development status
	@echo "=== Git Status ==="
	@git status --short
	@echo ""
	@echo "=== Recent Commits ==="
	@git log --oneline -5
	@echo ""
	@echo "=== Branch Info ==="
	@git branch -v
