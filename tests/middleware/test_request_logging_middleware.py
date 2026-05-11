"""Unit tests for the request_logging_middleware module."""

from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fastapi import FastAPI, Request, Response

from python_template_server.middleware import RequestLoggingMiddleware


class TestRequestLoggingMiddleware:
    """Unit tests for RequestLoggingMiddleware."""

    def test_init(self, mock_app: FastAPI) -> None:
        """Test middleware initialization."""
        middleware = RequestLoggingMiddleware(mock_app)
        assert middleware.logger is not None

    @pytest.mark.asyncio
    async def test_dispatch_logs_request_and_response(
        self, mock_app: FastAPI, mock_request: Request, mock_response: Response
    ) -> None:
        """Test that dispatch logs both request and response."""
        assert mock_request.client is not None  # Ensure client is set for this test

        middleware = RequestLoggingMiddleware(mock_app)

        # Mock the call_next function
        call_next = AsyncMock(return_value=mock_response)

        # Mock the logger
        middleware.logger = MagicMock()

        result = await middleware.dispatch(mock_request, call_next)

        assert result == mock_response
        middleware.logger.info.assert_has_calls(
            [
                call("Request: %s %s from %s:%d", "GET", "/test", "127.0.0.1", mock_request.client.port),
                call("Response: %s %s -> %d", "GET", "/test", 200),
            ]
        )

    @pytest.mark.asyncio
    async def test_dispatch_handles_missing_client(self, mock_app: FastAPI, mock_response: Response) -> None:
        """Test that dispatch handles requests with no client information."""
        middleware = RequestLoggingMiddleware(mock_app)

        # Create request without client
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/endpoint"
        request.client = None

        call_next = AsyncMock(return_value=mock_response)
        middleware.logger = MagicMock()

        result = await middleware.dispatch(request, call_next)

        assert result == mock_response
        middleware.logger.info.assert_any_call("Request: %s %s from %s:%d", "POST", "/api/endpoint", "unknown", 0)
