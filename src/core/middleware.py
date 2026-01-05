"""Middleware components for the FastAPI application.

This module provides middleware functions for logging, monitoring,
and request/response processing.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming HTTP requests with timing information.

    This middleware logs the HTTP method, path, query parameters,
    status code, and response time for each request. It helps with
    debugging, monitoring, and performance analysis.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process the request and log timing information.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            Response: The HTTP response from the application.
        """
        # Record start time
        start_time = time.time()

        # Build request info for logging
        method = request.method
        path = request.url.path
        query_params = str(request.url.query) if request.url.query else ""

        # Log incoming request
        logger.info(
            f"Request started: {method} {path}"
            + (f"?{query_params}" if query_params else "")
        )

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)

        # Log request completion with timing
        logger.info(
            f"Request completed: {method} {path} "
            f"- Status: {response.status_code} "
            f"- Duration: {process_time_ms}ms"
        )

        # Add timing header to response
        response.headers["X-Process-Time"] = str(process_time_ms)

        return response
