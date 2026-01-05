"""Main FastAPI application factory and configuration.

This module provides the create_app() factory function for initializing
the FastAPI application with proper configuration and metadata.
"""

from fastapi import FastAPI

from src.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    This factory function initializes a new FastAPI application with
    configuration values from the application settings, including
    title, description, version, and other metadata.

    Returns:
        FastAPI: Configured FastAPI application instance ready to use.

    Example:
        >>> app = create_app()
        >>> # App is now ready to be run with uvicorn
    """
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
    )

    return app


# Application instance for uvicorn to discover
app = create_app()
