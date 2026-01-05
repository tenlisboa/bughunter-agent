"""Pytest configuration and fixtures for testing.

This module provides shared pytest fixtures for the test suite,
including the FastAPI test client fixture.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI TestClient for testing endpoints.

    This fixture creates a new FastAPI application instance using the
    create_app() factory function and wraps it in a TestClient for
    making test requests.

    Yields:
        TestClient: A FastAPI TestClient instance for making HTTP requests
            in tests without actually starting the server.

    Example:
        >>> def test_health_endpoint(client):
        ...     response = client.get("/health")
        ...     assert response.status_code == 200
    """
    app = create_app()
    return TestClient(app)
