# ArchBuilder.AI Cloud Server - Development Commands
# Makefile for easy development workflow management

.PHONY: help install test test-unit test-integration test-security test-fast test-slow coverage lint format type-check pre-commit clean docs serve dev

# Default target
help:
	@echo "ArchBuilder.AI Cloud Server - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  install          Install all dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-security    Run security tests only"
	@echo "  test-ai          Run AI-related tests only"
	@echo "  test-database    Run database tests only"
	@echo "  test-fast        Run fast tests only (exclude slow)"
	@echo "  test-slow        Run slow tests only"
	@echo "  test-parallel    Run tests in parallel"
	@echo "  test-failed      Run last failed tests only"
	@echo "  coverage         Run tests with coverage report"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint             Run all linters (ruff, mypy)"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run type checking with mypy"
	@echo "  pre-commit       Run pre-commit hooks"
	@echo ""
	@echo "Development Commands:"
	@echo "  dev              Start development server"
	@echo "  serve            Start production server"
	@echo "  clean            Clean up generated files"
	@echo "  docs             Generate documentation"
	@echo ""
	@echo "Database Commands:"
	@echo "  db-init          Initialize database"
	@echo "  db-migrate       Run database migrations"
	@echo "  db-upgrade       Upgrade database to latest"
	@echo "  db-reset         Reset database (WARNING: destroys data)"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	python run_tests.py

test-unit:
	python run_tests.py --unit

test-integration:
	python run_tests.py --integration

test-security:
	python run_tests.py --security

test-ai:
	python run_tests.py --ai

test-database:
	python run_tests.py --database

test-fast:
	python run_tests.py --fast

test-slow:
	python run_tests.py --slow

test-parallel:
	python run_tests.py --parallel

test-failed:
	python run_tests.py --lf

coverage:
	python run_tests.py --coverage

# Code Quality
lint:
	@echo "Running ruff..."
	ruff check .
	@echo "Running mypy..."
	mypy app

format:
	@echo "Running black..."
	black .
	@echo "Running isort..."
	isort .
	@echo "Running ruff fix..."
	ruff check --fix .

type-check:
	mypy app

pre-commit:
	pre-commit run --all-files

# Development
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

serve:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

clean:
	@echo "Cleaning up..."
	rm -rf __pycache__ .pytest_cache .mypy_cache .coverage htmlcov
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

docs:
	@echo "Generating documentation..."
	# Add documentation generation commands here

# Database
db-init:
	@echo "Initializing database..."
	python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"

db-migrate:
	@echo "Creating database migration..."
	alembic revision --autogenerate -m "Auto migration"

db-upgrade:
	@echo "Upgrading database..."
	alembic upgrade head

db-reset:
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	@echo "Resetting database..."
	rm -f app.db
	alembic upgrade head

# CI/CD Helper Commands
ci-install:
	pip install -e ".[dev,prod]"

ci-test:
	python run_tests.py --coverage --verbose

ci-lint:
	ruff check .
	mypy app
	black --check .
	isort --check-only .

ci-security:
	python run_tests.py --security
	# Add bandit security scanning
	# bandit -r app

# Performance Testing
perf-test:
	@echo "Running performance tests..."
	python run_tests.py --slow

load-test:
	@echo "Running load tests..."
	# Add load testing commands here (e.g., locust)

# Container Commands
docker-build:
	docker build -t archbuilder-ai-server .

docker-run:
	docker run -p 8000:8000 archbuilder-ai-server

docker-test:
	docker run --rm archbuilder-ai-server python run_tests.py

# Environment Setup
env-dev:
	@echo "Setting up development environment..."
	cp .env.example .env
	@echo "Please edit .env file with your configuration"

env-test:
	@echo "Setting up test environment..."
	export ENVIRONMENT=test

# Monitoring and Profiling
profile:
	@echo "Running with profiling..."
	python -m cProfile -o profile.stats -m uvicorn app.main:app

monitor:
	@echo "Starting monitoring..."
	# Add monitoring commands here

# Release Commands
version-patch:
	bump2version patch

version-minor:
	bump2version minor

version-major:
	bump2version major

release:
	@echo "Creating release..."
	# Add release commands here