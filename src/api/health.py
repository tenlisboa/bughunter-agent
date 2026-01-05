"""Health check endpoint for monitoring application status.

This module provides a simple health check endpoint that returns
information about the application's status, version, and service availability.
"""

import logging

from fastapi import APIRouter

from src.config import settings
from src.models import HealthResponse

logger = logging.getLogger(__name__)

# Create router for health endpoint
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=200,
    summary="Health Check",
    description="Returns the current health status of the application including version and environment information.",
)
async def health_check() -> HealthResponse:
    """Check the health status of the application.

    This endpoint provides information about the application's current state,
    including version, environment, and service status. It's useful for
    monitoring tools and load balancers to verify the application is running.

    Returns:
        HealthResponse: Health status information including:
            - status: Overall health status ('healthy' or 'unhealthy')
            - version: Current application version
            - environment: Current environment (development, staging, production)
            - database: Database connection status (placeholder for now)

    Example:
        >>> response = await health_check()
        >>> response.status
        'healthy'
        >>> response.version
        '0.1.0'
    """
    logger.debug("Health check requested")

    # For now, we always return healthy status
    # In the future, this could check database connections, external services, etc.
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        database=None,  # Placeholder - will be implemented when database is added
    )
