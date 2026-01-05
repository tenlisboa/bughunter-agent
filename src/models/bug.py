"""Pydantic models for bug report data and webhook payloads."""

from typing import Optional

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
