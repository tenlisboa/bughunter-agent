"""Tests for Pydantic model validation.

This module contains tests for the webhook payload models to verify they
correctly validate and reject invalid data according to their field constraints.
"""

import pytest
from pydantic import ValidationError

from src.models import (
    BugBody,
    DatadogWebhookPayload,
    HealthResponse,
    StackTraceFrame,
    WebhookErrorResponse,
    WebhookProcessedResponse,
    WebhookResponse,
    WebhookSkippedResponse,
)


class TestStackTraceFrame:
    """Tests for the StackTraceFrame model."""

    def test_valid_stack_trace_frame(self) -> None:
        """Test that StackTraceFrame accepts valid data.

        Verifies:
            - Model accepts all required fields with valid values
            - Optional class_name field can be provided via dict
            - All fields are correctly typed
        """
        data = {
            "file": "/app/src/services/payment.py",
            "line": 42,
            "function": "process_payment",
            "class": "PaymentService",
        }
        frame = StackTraceFrame(**data)

        assert frame.file == "/app/src/services/payment.py"
        assert frame.line == 42
        assert frame.function == "process_payment"
        assert frame.class_name == "PaymentService"

    def test_valid_stack_trace_frame_without_class(self) -> None:
        """Test that StackTraceFrame accepts valid data without class_name.

        Verifies:
            - Model accepts required fields only
            - class_name defaults to None when not provided
        """
        frame = StackTraceFrame(
            file="/app/src/api/checkout.py",
            line=128,
            function="checkout",
        )

        assert frame.file == "/app/src/api/checkout.py"
        assert frame.line == 128
        assert frame.function == "checkout"
        assert frame.class_name is None

    def test_stack_trace_frame_with_class_alias(self) -> None:
        """Test that StackTraceFrame accepts 'class' as an alias for class_name.

        Verifies:
            - Model accepts 'class' field name in JSON data
            - Field is mapped to class_name attribute
        """
        data = {
            "file": "/app/src/services/payment.py",
            "line": 42,
            "function": "process_payment",
            "class": "PaymentService",
        }
        frame = StackTraceFrame(**data)

        assert frame.class_name == "PaymentService"

    def test_stack_trace_frame_rejects_empty_file(self) -> None:
        """Test that StackTraceFrame rejects empty file path.

        Verifies:
            - Model rejects empty string for file field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            StackTraceFrame(
                file="",
                line=42,
                function="process_payment",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("file",) for error in errors)

    def test_stack_trace_frame_rejects_empty_function(self) -> None:
        """Test that StackTraceFrame rejects empty function name.

        Verifies:
            - Model rejects empty string for function field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            StackTraceFrame(
                file="/app/src/services/payment.py",
                line=42,
                function="",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("function",) for error in errors)

    def test_stack_trace_frame_rejects_zero_line(self) -> None:
        """Test that StackTraceFrame rejects line number zero.

        Verifies:
            - Model rejects line=0 (constraint: ge=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            StackTraceFrame(
                file="/app/src/services/payment.py",
                line=0,
                function="process_payment",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("line",) for error in errors)

    def test_stack_trace_frame_rejects_negative_line(self) -> None:
        """Test that StackTraceFrame rejects negative line number.

        Verifies:
            - Model rejects negative line numbers (constraint: ge=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            StackTraceFrame(
                file="/app/src/services/payment.py",
                line=-1,
                function="process_payment",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("line",) for error in errors)

    def test_stack_trace_frame_rejects_missing_required_fields(self) -> None:
        """Test that StackTraceFrame rejects data missing required fields.

        Verifies:
            - Model rejects data missing file field
            - Model rejects data missing line field
            - Model rejects data missing function field
            - ValidationError is raised with appropriate errors
        """
        with pytest.raises(ValidationError) as exc_info:
            StackTraceFrame()

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "file" in error_fields
        assert "line" in error_fields
        assert "function" in error_fields


class TestBugBody:
    """Tests for the BugBody model."""

    def test_valid_bug_body(self) -> None:
        """Test that BugBody accepts valid data.

        Verifies:
            - Model accepts all required fields with valid values
            - Model accepts optional context field
            - stack_trace list contains StackTraceFrame objects
        """
        bug_body = BugBody(
            error_class="ValueError",
            error_message="Invalid payment amount: -100.00",
            stack_trace=[
                StackTraceFrame(
                    **{
                        "file": "/app/src/services/payment.py",
                        "line": 42,
                        "function": "process_payment",
                        "class": "PaymentService",
                    }
                ),
                StackTraceFrame(
                    file="/app/src/api/checkout.py",
                    line=128,
                    function="checkout",
                ),
            ],
            context={
                "user_id": "12345",
                "transaction_id": "txn_abc123",
                "environment": "production",
            },
        )

        assert bug_body.error_class == "ValueError"
        assert bug_body.error_message == "Invalid payment amount: -100.00"
        assert len(bug_body.stack_trace) == 2
        assert isinstance(bug_body.stack_trace[0], StackTraceFrame)
        assert bug_body.context["user_id"] == "12345"

    def test_valid_bug_body_without_context(self) -> None:
        """Test that BugBody accepts valid data without context.

        Verifies:
            - Model accepts required fields only
            - context defaults to None when not provided
        """
        bug_body = BugBody(
            error_class="NullPointerException",
            error_message="Cannot call method on null",
            stack_trace=[
                StackTraceFrame(
                    file="/app/src/services/payment.py",
                    line=42,
                    function="process_payment",
                ),
            ],
        )

        assert bug_body.error_class == "NullPointerException"
        assert bug_body.error_message == "Cannot call method on null"
        assert len(bug_body.stack_trace) == 1
        assert bug_body.context is None

    def test_bug_body_rejects_empty_error_class(self) -> None:
        """Test that BugBody rejects empty error_class.

        Verifies:
            - Model rejects empty string for error_class field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            BugBody(
                error_class="",
                error_message="Invalid payment amount",
                stack_trace=[
                    StackTraceFrame(
                        file="/app/src/services/payment.py",
                        line=42,
                        function="process_payment",
                    ),
                ],
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("error_class",) for error in errors)

    def test_bug_body_rejects_empty_error_message(self) -> None:
        """Test that BugBody rejects empty error_message.

        Verifies:
            - Model rejects empty string for error_message field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            BugBody(
                error_class="ValueError",
                error_message="",
                stack_trace=[
                    StackTraceFrame(
                        file="/app/src/services/payment.py",
                        line=42,
                        function="process_payment",
                    ),
                ],
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("error_message",) for error in errors)

    def test_bug_body_rejects_empty_stack_trace(self) -> None:
        """Test that BugBody rejects empty stack_trace list.

        Verifies:
            - Model rejects empty list for stack_trace (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            BugBody(
                error_class="ValueError",
                error_message="Invalid payment amount",
                stack_trace=[],
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("stack_trace",) for error in errors)

    def test_bug_body_rejects_invalid_stack_trace_frame(self) -> None:
        """Test that BugBody rejects invalid StackTraceFrame in stack_trace.

        Verifies:
            - Model validates each StackTraceFrame in stack_trace list
            - ValidationError is raised for invalid nested model
        """
        with pytest.raises(ValidationError) as exc_info:
            BugBody(
                error_class="ValueError",
                error_message="Invalid payment amount",
                stack_trace=[
                    {
                        "file": "/app/src/services/payment.py",
                        "line": 0,  # Invalid: line must be >= 1
                        "function": "process_payment",
                    }
                ],
            )

        errors = exc_info.value.errors()
        assert any("stack_trace" in error["loc"] for error in errors)


class TestDatadogWebhookPayload:
    """Tests for the DatadogWebhookPayload model."""

    def test_valid_webhook_payload(self) -> None:
        """Test that DatadogWebhookPayload accepts valid data.

        Verifies:
            - Model accepts all required fields with valid values
            - Model accepts optional tags field
            - Nested BugBody is correctly validated
        """
        payload = DatadogWebhookPayload(
            id="1234567890",
            title="Error: NullPointerException in PaymentService",
            alert_type="error",
            priority="critical",
            tags=["env:production", "service:px-backend", "version:2.3.1"],
            body=BugBody(
                error_class="NullPointerException",
                error_message="Cannot call method on null",
                stack_trace=[
                    StackTraceFrame(
                        **{
                            "file": "src/Services/PaymentService.php",
                            "line": 145,
                            "function": "process",
                            "class": "App\\Services\\PaymentService",
                        }
                    ),
                ],
            ),
            date_happened=1699900000,
        )

        assert payload.id == "1234567890"
        assert payload.title == "Error: NullPointerException in PaymentService"
        assert payload.alert_type == "error"
        assert payload.priority == "critical"
        assert len(payload.tags) == 3
        assert isinstance(payload.body, BugBody)
        assert payload.date_happened == 1699900000

    def test_valid_webhook_payload_without_tags(self) -> None:
        """Test that DatadogWebhookPayload accepts valid data without tags.

        Verifies:
            - Model accepts required fields only
            - tags defaults to empty list when not provided
        """
        payload = DatadogWebhookPayload(
            id="1234567890",
            title="Error: NullPointerException in PaymentService",
            alert_type="error",
            priority="critical",
            body=BugBody(
                error_class="NullPointerException",
                error_message="Cannot call method on null",
                stack_trace=[
                    StackTraceFrame(
                        file="src/Services/PaymentService.php",
                        line=145,
                        function="process",
                    ),
                ],
            ),
            date_happened=1699900000,
        )

        assert payload.tags == []

    def test_webhook_payload_rejects_empty_id(self) -> None:
        """Test that DatadogWebhookPayload rejects empty id.

        Verifies:
            - Model rejects empty string for id field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            DatadogWebhookPayload(
                id="",
                title="Error: NullPointerException in PaymentService",
                alert_type="error",
                priority="critical",
                body=BugBody(
                    error_class="NullPointerException",
                    error_message="Cannot call method on null",
                    stack_trace=[
                        StackTraceFrame(
                            file="src/Services/PaymentService.php",
                            line=145,
                            function="process",
                        ),
                    ],
                ),
                date_happened=1699900000,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("id",) for error in errors)

    def test_webhook_payload_rejects_empty_title(self) -> None:
        """Test that DatadogWebhookPayload rejects empty title.

        Verifies:
            - Model rejects empty string for title field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            DatadogWebhookPayload(
                id="1234567890",
                title="",
                alert_type="error",
                priority="critical",
                body=BugBody(
                    error_class="NullPointerException",
                    error_message="Cannot call method on null",
                    stack_trace=[
                        StackTraceFrame(
                            file="src/Services/PaymentService.php",
                            line=145,
                            function="process",
                        ),
                    ],
                ),
                date_happened=1699900000,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("title",) for error in errors)

    def test_webhook_payload_rejects_empty_alert_type(self) -> None:
        """Test that DatadogWebhookPayload rejects empty alert_type.

        Verifies:
            - Model rejects empty string for alert_type field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            DatadogWebhookPayload(
                id="1234567890",
                title="Error: NullPointerException in PaymentService",
                alert_type="",
                priority="critical",
                body=BugBody(
                    error_class="NullPointerException",
                    error_message="Cannot call method on null",
                    stack_trace=[
                        StackTraceFrame(
                            file="src/Services/PaymentService.php",
                            line=145,
                            function="process",
                        ),
                    ],
                ),
                date_happened=1699900000,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("alert_type",) for error in errors)

    def test_webhook_payload_rejects_empty_priority(self) -> None:
        """Test that DatadogWebhookPayload rejects empty priority.

        Verifies:
            - Model rejects empty string for priority field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            DatadogWebhookPayload(
                id="1234567890",
                title="Error: NullPointerException in PaymentService",
                alert_type="error",
                priority="",
                body=BugBody(
                    error_class="NullPointerException",
                    error_message="Cannot call method on null",
                    stack_trace=[
                        StackTraceFrame(
                            file="src/Services/PaymentService.php",
                            line=145,
                            function="process",
                        ),
                    ],
                ),
                date_happened=1699900000,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("priority",) for error in errors)

    def test_webhook_payload_rejects_negative_date_happened(self) -> None:
        """Test that DatadogWebhookPayload rejects negative date_happened.

        Verifies:
            - Model rejects negative timestamp (constraint: ge=0)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            DatadogWebhookPayload(
                id="1234567890",
                title="Error: NullPointerException in PaymentService",
                alert_type="error",
                priority="critical",
                body=BugBody(
                    error_class="NullPointerException",
                    error_message="Cannot call method on null",
                    stack_trace=[
                        StackTraceFrame(
                            file="src/Services/PaymentService.php",
                            line=145,
                            function="process",
                        ),
                    ],
                ),
                date_happened=-1,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("date_happened",) for error in errors)

    def test_webhook_payload_rejects_invalid_body(self) -> None:
        """Test that DatadogWebhookPayload rejects invalid BugBody.

        Verifies:
            - Model validates nested BugBody model
            - ValidationError is raised for invalid nested model
        """
        with pytest.raises(ValidationError) as exc_info:
            DatadogWebhookPayload(
                id="1234567890",
                title="Error: NullPointerException in PaymentService",
                alert_type="error",
                priority="critical",
                body={
                    "error_class": "",  # Invalid: min_length=1
                    "error_message": "Cannot call method on null",
                    "stack_trace": [
                        {
                            "file": "src/Services/PaymentService.php",
                            "line": 145,
                            "function": "process",
                        },
                    ],
                },
                date_happened=1699900000,
            )

        errors = exc_info.value.errors()
        assert any("body" in error["loc"] for error in errors)


class TestHealthResponse:
    """Tests for the HealthResponse model."""

    def test_valid_health_response(self) -> None:
        """Test that HealthResponse accepts valid data.

        Verifies:
            - Model accepts all required fields with valid values
            - database field can be None or a dictionary
        """
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            environment="development",
            database=None,
        )

        assert response.status == "healthy"
        assert response.version == "0.1.0"
        assert response.environment == "development"
        assert response.database is None

    def test_health_response_with_database_info(self) -> None:
        """Test that HealthResponse accepts database information.

        Verifies:
            - Model accepts dictionary for database field
        """
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            environment="production",
            database={"status": "connected", "name": "px-bughunter"},
        )

        assert response.database["status"] == "connected"
        assert response.database["name"] == "px-bughunter"

    def test_health_response_rejects_empty_status(self) -> None:
        """Test that HealthResponse rejects empty status.

        Verifies:
            - Model rejects empty string for status field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            HealthResponse(
                status="",
                version="0.1.0",
                environment="development",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("status",) for error in errors)


class TestWebhookResponses:
    """Tests for webhook response models."""

    def test_valid_webhook_response(self) -> None:
        """Test that WebhookResponse accepts valid data.

        Verifies:
            - Model accepts all required fields with valid values
        """
        response = WebhookResponse(
            status="success",
            message="Webhook processed successfully",
        )

        assert response.status == "success"
        assert response.message == "Webhook processed successfully"

    def test_valid_webhook_processed_response(self) -> None:
        """Test that WebhookProcessedResponse accepts valid data.

        Verifies:
            - Model accepts all required fields including bug_id
            - Model inherits from WebhookResponse
        """
        response = WebhookProcessedResponse(
            status="success",
            message="Bug report created successfully",
            bug_id="bug_1234567890",
        )

        assert response.status == "success"
        assert response.message == "Bug report created successfully"
        assert response.bug_id == "bug_1234567890"

    def test_valid_webhook_skipped_response(self) -> None:
        """Test that WebhookSkippedResponse accepts valid data.

        Verifies:
            - Model accepts all required fields including reason
            - Model inherits from WebhookResponse
        """
        response = WebhookSkippedResponse(
            status="skipped",
            message="Webhook skipped due to duplicate detection",
            reason="Bug report already exists for this error",
        )

        assert response.status == "skipped"
        assert response.message == "Webhook skipped due to duplicate detection"
        assert response.reason == "Bug report already exists for this error"

    def test_valid_webhook_error_response(self) -> None:
        """Test that WebhookErrorResponse accepts valid data.

        Verifies:
            - Model accepts all required fields
            - Optional error_detail can be provided
            - Model inherits from WebhookResponse
        """
        response = WebhookErrorResponse(
            status="error",
            message="Failed to process webhook",
            error_detail="Invalid payload format: missing required field 'body'",
        )

        assert response.status == "error"
        assert response.message == "Failed to process webhook"
        assert response.error_detail == "Invalid payload format: missing required field 'body'"

    def test_webhook_error_response_without_error_detail(self) -> None:
        """Test that WebhookErrorResponse accepts data without error_detail.

        Verifies:
            - error_detail is optional and defaults to None
        """
        response = WebhookErrorResponse(
            status="error",
            message="Failed to process webhook",
        )

        assert response.error_detail is None

    def test_webhook_response_rejects_empty_status(self) -> None:
        """Test that WebhookResponse rejects empty status.

        Verifies:
            - Model rejects empty string for status field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            WebhookResponse(
                status="",
                message="Webhook processed successfully",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("status",) for error in errors)

    def test_webhook_response_rejects_empty_message(self) -> None:
        """Test that WebhookResponse rejects empty message.

        Verifies:
            - Model rejects empty string for message field (min_length=1)
            - ValidationError is raised with appropriate error
        """
        with pytest.raises(ValidationError) as exc_info:
            WebhookResponse(
                status="success",
                message="",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("message",) for error in errors)
