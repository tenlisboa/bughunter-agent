"""Pydantic models for bug report data and webhook payloads."""

from typing import Any

from pydantic import BaseModel, Field


class StackTraceFrame(BaseModel):
    """Represents a single frame in a stack trace.

    This model captures the essential information about where an error occurred
    in the code, including file location, line number, and execution context.
    """

    file: str = Field(
        ...,
        description="File path where the code executed",
        min_length=1,
    )
    line: int = Field(
        ...,
        description="Line number in the file",
        ge=1,
    )
    function: str = Field(
        ...,
        description="Function or method name being executed",
        min_length=1,
    )
    class_name: str | None = Field(
        default=None,
        description="Class name if the function is a method, None otherwise",
        alias="class",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "file": "/app/src/services/payment.py",
                    "line": 42,
                    "function": "process_payment",
                    "class": "PaymentService",
                }
            ]
        }
    }


class BugBody(BaseModel):
    """Represents the body of a bug report containing error details.

    This model captures the complete error information including the error type,
    message, full stack trace, and any additional contextual information that
    may be useful for debugging.
    """

    error_class: str = Field(
        ...,
        description="The class or type of error that occurred (e.g., 'ValueError', 'NullPointerException')",
        min_length=1,
    )
    error_message: str = Field(
        ...,
        description="The error message describing what went wrong",
        min_length=1,
    )
    stack_trace: list[StackTraceFrame] = Field(
        ...,
        description="List of stack trace frames showing the execution path that led to the error",
        min_length=1,
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context information such as environment variables, request data, or custom metadata",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_class": "ValueError",
                    "error_message": "Invalid payment amount: -100.00",
                    "stack_trace": [
                        {
                            "file": "/app/src/services/payment.py",
                            "line": 42,
                            "function": "process_payment",
                            "class": "PaymentService",
                        },
                        {
                            "file": "/app/src/api/checkout.py",
                            "line": 128,
                            "function": "checkout",
                        },
                    ],
                    "context": {
                        "user_id": "12345",
                        "transaction_id": "txn_abc123",
                        "environment": "production",
                    },
                }
            ]
        }
    }


class DatadogWebhookPayload(BaseModel):
    """Represents a complete webhook payload from Datadog.

    This model captures the full structure of a Datadog alert webhook including
    metadata, alert details, and the bug report body. It validates the incoming
    webhook data before processing.
    """

    id: str = Field(
        ...,
        description="Unique identifier for this alert event",
        min_length=1,
    )
    title: str = Field(
        ...,
        description="Human-readable title of the alert",
        min_length=1,
    )
    alert_type: str = Field(
        ...,
        description="Type of alert (e.g., 'error', 'warning', 'info')",
        min_length=1,
    )
    priority: str = Field(
        ...,
        description="Alert priority level (e.g., 'critical', 'high', 'medium', 'low')",
        min_length=1,
    )
    tags: list[str] = Field(
        default_factory=list,
        description="List of tags associated with the alert (e.g., environment, service, version)",
    )
    body: BugBody = Field(
        ...,
        description="Detailed bug report information including error details and stack trace",
    )
    date_happened: int = Field(
        ...,
        description="Unix timestamp (seconds) when the event occurred",
        ge=0,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
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
                            },
                            {
                                "file": "src/Utils/ValidationUtil.php",
                                "line": 67,
                                "function": "validate",
                                "class": "App\\Utils\\ValidationUtil",
                            },
                        ],
                        "context": {
                            "user_id": "12345",
                            "request_path": "/api/v1/payments",
                            "request_method": "POST",
                        },
                    },
                    "date_happened": 1699900000,
                }
            ]
        }
    }
