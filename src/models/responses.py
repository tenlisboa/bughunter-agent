"""Pydantic models for API response validation."""


from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model.

    This model represents the response from the health check endpoint,
    providing information about the application status, version, and
    service availability.
    """

    status: str = Field(
        ...,
        description="Overall health status of the application (e.g., 'healthy', 'unhealthy')",
        min_length=1,
    )
    version: str = Field(
        ...,
        description="Current version of the application",
        min_length=1,
    )
    environment: str = Field(
        ...,
        description="Current environment (development, staging, production)",
        min_length=1,
    )
    database: dict[str, str] | None = Field(
        default=None,
        description="Database connection status (placeholder for now)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": "0.1.0",
                    "environment": "development",
                    "database": None,
                }
            ]
        }
    }


class WebhookResponse(BaseModel):
    """Base webhook response model.

    This model represents the common structure for all webhook endpoint responses,
    including status and a human-readable message.
    """

    status: str = Field(
        ...,
        description="Response status (success, skipped, error)",
        min_length=1,
    )
    message: str = Field(
        ...,
        description="Human-readable message describing the result",
        min_length=1,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "message": "Webhook processed successfully",
                }
            ]
        }
    }


class WebhookProcessedResponse(WebhookResponse):
    """Response model for successfully processed webhooks.

    This model extends the base webhook response with additional information
    about the created bug report.
    """

    bug_id: str = Field(
        ...,
        description="Unique identifier of the created bug report",
        min_length=1,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "message": "Bug report created successfully",
                    "bug_id": "bug_1234567890",
                }
            ]
        }
    }


class WebhookSkippedResponse(WebhookResponse):
    """Response model for skipped webhooks.

    This model extends the base webhook response with information about
    why the webhook was skipped.
    """

    reason: str = Field(
        ...,
        description="Reason why the webhook was skipped",
        min_length=1,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "skipped",
                    "message": "Webhook skipped due to duplicate detection",
                    "reason": "Bug report already exists for this error",
                }
            ]
        }
    }


class WebhookErrorResponse(WebhookResponse):
    """Response model for error responses.

    This model extends the base webhook response with additional
    error details for debugging purposes.
    """

    error_detail: str | None = Field(
        default=None,
        description="Additional error information for debugging",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "error",
                    "message": "Failed to process webhook",
                    "error_detail": "Invalid payload format: missing required field 'body'",
                }
            ]
        }
    }
