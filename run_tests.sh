#!/bin/bash

# run_tests.sh - Run tests using the virtual environment
# This ensures all dependencies (including httpx) are available

set -e  # Exit on error

echo "========================================"
echo "PX BugHunter - Running Tests"
echo "========================================"
echo ""

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run ./init.sh first to set up the environment."
    exit 1
fi

# Run tests with the venv's Python
echo "Running pytest with virtual environment..."
.venv/bin/python -m pytest "$@"
