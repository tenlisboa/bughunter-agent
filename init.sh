#!/bin/bash

# init.sh - Setup script for px-bughunter FastAPI application
# Creates virtual environment and installs all dependencies

set -e  # Exit on error

echo "========================================"
echo "PX BugHunter - Environment Setup"
echo "========================================"
echo ""

# Check for Python 3.11+
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required. Found Python $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION found"
echo ""

# Create virtual environment
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment..."
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created at $VENV_DIR"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --quiet --upgrade pip
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing project dependencies..."
pip install --quiet -e ".[dev]"
echo "✓ Dependencies installed"
echo ""

# Verify installation
echo "Verifying installation..."
if python3 -c "import fastapi; import uvicorn; import pydantic" 2>/dev/null; then
    echo "✓ Core dependencies verified"
else
    echo "⚠ Warning: Could not verify some core dependencies"
fi
echo ""

echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To start the application (once implemented), run:"
echo "  uvicorn src.main:app --reload"
echo ""
