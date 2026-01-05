"""Main FastAPI application factory and configuration.

This module provides the create_app() factory function for initializing
the FastAPI application with proper configuration and metadata.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.config import settings
from src.core import (
    RequestLoggingMiddleware,
    generic_exception_handler,
    validation_exception_handler,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    This factory function initializes a new FastAPI application with
    configuration values from the application settings, including
    title, description, version, and other metadata. It also configures
    CORS middleware based on settings.

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

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Configure request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Register exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    return app


# Application instance for uvicorn to discover
app = create_app()
