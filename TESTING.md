# Testing Guide

## Running Tests

### Quick Start

Use the provided test script:

```bash
./run_tests.sh ./tests
```

This script ensures all tests run with the correct Python virtual environment and all dependencies (including `httpx`) are available.

### Alternative Methods

#### Method 1: Using the Virtual Environment Python Directly

```bash
.venv/bin/python -m pytest ./tests
```

#### Method 2: Activate the Virtual Environment First

```bash
source .venv/bin/activate
pytest ./tests
```

#### Method 3: Run Specific Tests

```bash
# Run a specific test file
./run_tests.sh ./tests/test_config_global.py

# Run a specific test class
./run_tests.sh ./tests/test_config_global.py::TestLoadGlobalConfig

# Run a specific test
./run_tests.sh ./tests/test_config_global.py::TestLoadGlobalConfig::test_load_valid_global_config

# Run with verbose output
./run_tests.sh ./tests -v

# Run with coverage report
./run_tests.sh ./tests --cov=src --cov-report=html
```

## Common Issues

### ImportError: The starlette.testclient module requires the httpx package

**Error Message:**
```
RuntimeError: The starlette.testclient module requires the httpx package to be installed.
You can install this with:
    $ pip install httpx
```

**Cause:** Running `pytest ./tests` directly without activating the virtual environment or using the venv's Python.

**Solution:** Use one of the methods above (recommended: `./run_tests.sh ./tests`)

### Virtual Environment Not Found

**Error Message:**
```
Error: Virtual environment not found.
Please run ./init.sh first to set up the environment.
```

**Solution:** Initialize the project first:
```bash
./init.sh
```

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_config_global.py    # Global configuration tests (20 tests)
├── test_config_project.py   # Project configuration tests (25 tests)
├── test_config_manager.py   # Configuration manager tests (21 tests)
├── test_config_integration.py  # Integration tests (17 tests)
├── test_yaml_loader.py      # YAML loader tests (17 tests)
├── test_health.py           # Health endpoint tests (6 tests)
├── test_models.py           # Data model tests (32 tests)
└── test_webhook.py          # Webhook endpoint tests (14 tests)
```

**Total: 152 tests** with **94% code coverage**

## Test Coverage

View coverage report:

```bash
# Generate and view HTML coverage report
./run_tests.sh ./tests --cov=src --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Ensure virtual environment is set up
./init.sh

# Run all tests with coverage
./run_tests.sh ./tests --cov=src --cov-report=term --cov-report=xml

# Check exit code
if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Tests failed!"
    exit 1
fi
```

## Type Checking and Linting

```bash
# Activate virtual environment
source .venv/bin/activate

# Run mypy type checking (strict mode)
mypy --strict src/

# Run ruff linting
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/
```
