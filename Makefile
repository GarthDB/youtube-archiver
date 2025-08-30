.PHONY: help install install-dev test test-cov lint format type-check security clean build docs

# Default target
help:
	@echo "Available commands:"
	@echo "  install      Install package in production mode"
	@echo "  install-dev  Install package in development mode with all dev dependencies"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  lint         Run all linting checks (ruff, black, isort, mypy, bandit)"
	@echo "  format       Auto-format code with black and isort"
	@echo "  type-check   Run mypy type checking"
	@echo "  security     Run bandit security analysis"
	@echo "  clean        Clean build artifacts and cache"
	@echo "  build        Build package"
	@echo "  pre-commit   Install and run pre-commit hooks"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest

test-cov:
	pytest --cov=youtube_archiver --cov-report=term-missing --cov-report=html

test-integration:
	pytest tests/integration/ -v

# Code Quality
lint: type-check security
	ruff check .
	black --check .
	isort --check-only .

format:
	black .
	isort .
	ruff check --fix .

type-check:
	mypy src/youtube_archiver/

security:
	bandit -r src/youtube_archiver/

# Development
pre-commit:
	pre-commit install
	pre-commit run --all-files

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Build
build: clean
	python -m build

# Quick development cycle
dev-check: format lint test

# CI simulation
ci: install-dev lint test-cov security
