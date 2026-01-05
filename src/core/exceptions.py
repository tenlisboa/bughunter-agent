"""Exception handlers for the FastAPI application.

This module provides global exception handlers for validation errors,
HTTP exceptions, and unexpected exceptions to ensure consistent error
responses across the application.
"""

import logging
from typing import Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """Handle Pydantic validation errors with detailed error messages.

    This handler is triggered when request data fails Pydantic validation,
    either from FastAPI route parameters or from Pydantic model validation.
    It formats the validation errors into a user-friendly response.

    Args:
        request: The incoming HTTP request that caused the validation error.
        exc: The validation exception containing details about failed validations.

    Returns:
        JSONResponse: A 422 Unprocessable Entity response with validation error details.
    """
    # Extract validation error details
    errors = exc.errors() if hasattr(exc, "errors") else []

    # Format error messages for better readability
    formatted_errors = []
    for error in errors:
        loc = " -> ".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", "Validation error")
        error_type = error.get("type", "validation_error")

        formatted_errors.append(
            {
                "field": loc,
                "message": msg,
                "type": error_type,
            }
        )

    # Log validation error
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: "
        f"{len(formatted_errors)} field(s) failed validation"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation error: request data is invalid",
            "error_detail": "One or more fields failed validation",
            "errors": formatted_errors,
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions with generic error response.

    This handler catches all unexpected exceptions that are not handled
    by more specific handlers. It logs the full exception for debugging
    and returns a generic error message to the client.

    Args:
        request: The incoming HTTP request that caused the exception.
        exc: The exception that was raised.

    Returns:
        JSONResponse: A 500 Internal Server Error response.
    """
    # Log the exception with full traceback
    logger.exception(
        f"Unexpected error on {request.method} {request.url.path}: {str(exc)}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected error occurred while processing your request",
            "error_detail": "Internal server error",
        },
    )
