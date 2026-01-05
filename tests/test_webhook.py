"""Tests for the webhook endpoint.

This module contains tests for the POST /webhook/{project_id} endpoint to verify
it validates payloads correctly and handles both valid and invalid requests.
"""

import pytest
from fastapi.testclient import TestClient


def test_webhook_endpoint_accepts_valid_payload(client: TestClient) -> None:
    """Test that the webhook endpoint accepts a valid payload.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Status code is 501 (Not Implemented, as per placeholder design)
        - Response contains status and message fields
        - Endpoint processes valid DatadogWebhookPayload
    """
    payload = {
        "id": "1234567890",
        "title": "Error: NullPointerException in PaymentService",
        "alert_type": "error",
        "priority": "critical",
        "tags": ["env:production", "service:px-backend", "version:2.3.1"],
        "body": {
            "error_class": "NullPointerException",
            "error_message": "Cannot call method on null",
            "stack_trace": [
                {
                    "file": "src/Services/PaymentService.php",
                    "line": 145,
                    "function": "process",
                    "class": "App\\Services\\PaymentService",
                }
            ],
            "context": {
                "user_id": "12345",
                "transaction_id": "txn_abc123",
            },
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)

    assert response.status_code == 501
    json_data = response.json()
    assert "status" in json_data
    assert "message" in json_data
    assert json_data["status"] == "not_implemented"


def test_webhook_endpoint_validates_project_id(client: TestClient) -> None:
    """Test that the webhook endpoint validates project_id parameter.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint accepts valid project_id with various formats
        - project_id is properly passed to the endpoint
    """
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "high",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test error message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
        },
        "date_happened": 1699900000,
    }

    # Test with various valid project_id formats
    project_ids = ["my-project", "project_123", "PX-Backend", "test.project"]

    for project_id in project_ids:
        response = client.post(f"/webhook/{project_id}", json=payload)
        assert response.status_code == 501


def test_webhook_endpoint_rejects_missing_required_fields(client: TestClient) -> None:
    """Test that the webhook endpoint rejects payloads missing required fields.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint returns 422 Unprocessable Entity for invalid payloads
        - Validation errors are returned for missing fields
    """
    # Missing 'title' field
    payload = {
        "id": "1234567890",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 422


def test_webhook_endpoint_rejects_empty_string_fields(client: TestClient) -> None:
    """Test that the webhook endpoint rejects empty string fields.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint returns 422 for payloads with empty strings (min_length=1)
        - Validation errors identify the invalid field
    """
    # Empty 'title' field
    payload = {
        "id": "1234567890",
        "title": "",  # Invalid: min_length=1
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    # Custom exception handler returns 'errors' field
    assert "errors" in json_data or "detail" in json_data


def test_webhook_endpoint_rejects_invalid_nested_body(client: TestClient) -> None:
    """Test that the webhook endpoint rejects invalid nested BugBody.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint validates nested BugBody structure
        - Returns 422 for invalid nested data
    """
    # Invalid BugBody with empty error_class
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "",  # Invalid: min_length=1
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 422


def test_webhook_endpoint_rejects_empty_stack_trace(client: TestClient) -> None:
    """Test that the webhook endpoint rejects empty stack_trace.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint validates stack_trace has at least one frame (min_length=1)
        - Returns 422 for empty stack_trace list
    """
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [],  # Invalid: min_length=1
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 422


def test_webhook_endpoint_rejects_invalid_stack_trace_frame(client: TestClient) -> None:
    """Test that the webhook endpoint rejects invalid StackTraceFrame.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint validates each StackTraceFrame in stack_trace
        - Returns 422 for invalid frame data (e.g., line=0)
    """
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 0,  # Invalid: line must be >= 1
                    "function": "test",
                }
            ],
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 422


def test_webhook_endpoint_rejects_negative_date_happened(client: TestClient) -> None:
    """Test that the webhook endpoint rejects negative date_happened.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint validates date_happened is non-negative (ge=0)
        - Returns 422 for negative timestamps
    """
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
        },
        "date_happened": -1,  # Invalid: must be >= 0
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 422


def test_webhook_endpoint_accepts_payload_without_optional_fields(
    client: TestClient,
) -> None:
    """Test that the webhook endpoint accepts payload without optional fields.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint accepts payloads without optional fields (tags, context)
        - Response is successful with 501 status
    """
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
            # No context field
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 501


def test_webhook_endpoint_response_structure(client: TestClient) -> None:
    """Test that the webhook endpoint returns correct response structure.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Response contains status and message fields
        - Response conforms to WebhookResponse model
        - Content-Type is application/json
    """
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)

    # Verify response structure
    assert response.status_code == 501
    json_data = response.json()
    assert "status" in json_data
    assert "message" in json_data
    assert isinstance(json_data["status"], str)
    assert isinstance(json_data["message"], str)
    assert len(json_data["status"]) > 0
    assert len(json_data["message"]) > 0

    # Verify content type
    assert "application/json" in response.headers["content-type"]


def test_webhook_endpoint_response_model_validation(client: TestClient) -> None:
    """Test that the webhook endpoint response conforms to WebhookResponse model.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Response can be validated against WebhookResponse Pydantic model
        - All required fields are present and correctly typed
    """
    from src.models import WebhookResponse

    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    json_data = response.json()

    # Verify response validates against WebhookResponse model
    webhook_response = WebhookResponse(**json_data)
    assert webhook_response.status == "not_implemented"
    assert webhook_response.message == "Webhook endpoint is not yet implemented"


def test_webhook_endpoint_accepts_payload_with_context(client: TestClient) -> None:
    """Test that the webhook endpoint accepts payload with context field.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint accepts payloads with optional context field
        - Complex nested context data is validated correctly
    """
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": ["env:production"],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                }
            ],
            "context": {
                "user_id": "12345",
                "request_id": "req_abc123",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "nested": {
                    "key": "value",
                    "array": [1, 2, 3],
                },
            },
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 501


def test_webhook_endpoint_accepts_payload_with_class_field(client: TestClient) -> None:
    """Test that the webhook endpoint accepts stack frames with 'class' field.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint accepts 'class' field in StackTraceFrame (alias for class_name)
        - Field alias mapping works correctly
    """
    payload = {
        "id": "1234567890",
        "title": "Error: Test",
        "alert_type": "error",
        "priority": "critical",
        "tags": [],
        "body": {
            "error_class": "TestError",
            "error_message": "Test message",
            "stack_trace": [
                {
                    "file": "test.py",
                    "line": 1,
                    "function": "test",
                    "class": "TestClass",  # Using alias 'class' instead of 'class_name'
                }
            ],
        },
        "date_happened": 1699900000,
    }

    response = client.post("/webhook/my-project", json=payload)
    assert response.status_code == 501


def test_webhook_endpoint_rejects_malformed_json(client: TestClient) -> None:
    """Test that the webhook endpoint rejects malformed JSON.

    Args:
        client: FastAPI TestClient fixture for making requests

    Verifies:
        - Endpoint returns 422 for invalid JSON
        - Proper error handling for parse failures
    """
    response = client.post(
        "/webhook/my-project",
        data="{ invalid json }",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
