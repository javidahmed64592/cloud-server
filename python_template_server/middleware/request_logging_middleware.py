"""Middleware to log incoming requests and responses."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests and responses."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the RequestLoggingMiddleware."""
        super().__init__(app)
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Log request and response details."""
        client_ip = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else 0

        self.logger.info(
            "Request: %s %s from %s:%d",
            request.method,
            request.url.path,
            client_ip,
            client_port,
        )

        response = await call_next(request)

        self.logger.info(
            "Response: %s %s -> %d",
            request.method,
            request.url.path,
            response.status_code,
        )

        return response
