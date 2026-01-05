"""Webhook endpoint for receiving bug reports from Datadog.

This module provides the webhook endpoint that receives and validates
bug report payloads from Datadog alert webhooks.
"""

import logging

from fastapi import APIRouter, Path

from src.models import DatadogWebhookPayload, WebhookResponse

logger = logging.getLogger(__name__)

# Create router for webhook endpoint
router = APIRouter(tags=["Webhook"])


@router.post(
    "/webhook/{project_id}",
    response_model=WebhookResponse,
    status_code=501,
    summary="Receive Webhook from Datadog",
    description="Receives and validates bug report webhooks from Datadog. Currently returns 501 Not Implemented as a placeholder.",
)
async def receive_webhook(
    payload: DatadogWebhookPayload,
    project_id: str = Path(
        ...,
        description="Unique identifier for the project receiving the webhook",
        min_length=1,
    ),
) -> WebhookResponse:
    """Receive and process a webhook payload from Datadog.

    This endpoint validates the incoming webhook payload structure and
    will process bug reports in future implementations. For now, it
    returns a 501 Not Implemented status to indicate the endpoint is
    a placeholder.

    Args:
        project_id: Unique identifier for the project (path parameter)
        payload: Validated Datadog webhook payload containing bug report data

    Returns:
        WebhookResponse: Response indicating the webhook was received but not implemented

    Raises:
        HTTPException: If the payload validation fails (handled by FastAPI)

    Example:
        >>> payload = DatadogWebhookPayload(...)
        >>> response = await receive_webhook("my-project", payload)
        >>> response.status
        'not_implemented'
    """
    logger.info(f"Webhook received for project: {project_id}")
    logger.debug(f"Webhook payload ID: {payload.id}, Title: {payload.title}")

    # Return 501 Not Implemented as this is a placeholder endpoint
    # In the future, this will process the webhook and create bug reports
    return WebhookResponse(
        status="not_implemented",
        message="Webhook endpoint is not yet implemented",
    )
