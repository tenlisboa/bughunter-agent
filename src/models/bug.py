"""Pydantic models for bug report data and webhook payloads."""

from typing import Any, Optional

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
    class_name: Optional[str] = Field(
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
    context: Optional[dict[str, Any]] = Field(
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
