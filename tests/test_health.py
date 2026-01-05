"""Tests for the health check endpoint.

This module contains tests for the /health endpoint to verify it returns
the correct status code, response structure, and version information.
"""

import pytest
from fastapi.testclient import TestClient

from src.config import settings


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """Test that the health endpoint returns HTTP 200 OK.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Status code is 200
        - Response is successful
    """
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_response_structure(client: TestClient) -> None:
    """Test that the health endpoint returns correct response structure.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Response contains all required fields (status, version, environment, database)
        - All fields have the correct types
        - Status field is 'healthy'
    """
    response = client.get("/health")
    json_data = response.json()

    # Verify all required fields are present
    assert "status" in json_data
    assert "version" in json_data
    assert "environment" in json_data
    assert "database" in json_data

    # Verify field types
    assert isinstance(json_data["status"], str)
    assert isinstance(json_data["version"], str)
    assert isinstance(json_data["environment"], str)
    assert json_data["database"] is None or isinstance(json_data["database"], dict)

    # Verify status value
    assert json_data["status"] == "healthy"


def test_health_endpoint_version_matches_settings(client: TestClient) -> None:
    """Test that the health endpoint returns the correct version from settings.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Version field matches the application version from settings
        - Version is not empty
    """
    response = client.get("/health")
    json_data = response.json()

    # Verify version matches settings
    assert json_data["version"] == settings.app_version
    assert len(json_data["version"]) > 0


def test_health_endpoint_environment_matches_settings(client: TestClient) -> None:
    """Test that the health endpoint returns the correct environment from settings.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Environment field matches the environment from settings
        - Environment is not empty
    """
    response = client.get("/health")
    json_data = response.json()

    # Verify environment matches settings
    assert json_data["environment"] == settings.environment
    assert len(json_data["environment"]) > 0


def test_health_endpoint_content_type(client: TestClient) -> None:
    """Test that the health endpoint returns JSON content type.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Content-Type header is application/json
    """
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]


def test_health_endpoint_response_model_validation(client: TestClient) -> None:
    """Test that the health endpoint response conforms to HealthResponse model.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Response can be validated against the HealthResponse Pydantic model
        - All required fields are present and correctly typed
    """
    from src.models import HealthResponse

    response = client.get("/health")
    json_data = response.json()

    # Verify response validates against HealthResponse model
    health_response = HealthResponse(**json_data)
    assert health_response.status == "healthy"
    assert health_response.version == settings.app_version
    assert health_response.environment == settings.environment
    assert health_response.database is None
