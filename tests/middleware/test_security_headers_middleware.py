"""Unit tests for the security_headers_middleware module."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request, Response

from python_template_server.middleware import SecurityHeadersMiddleware

HSTS_ONE_YEAR = 31536000


class TestSecurityHeadersMiddleware:
    """Unit tests for SecurityHeadersMiddleware."""

    def test_init(self, mock_app: FastAPI) -> None:
        """Test middleware initialization."""
        middleware = SecurityHeadersMiddleware(mock_app, hsts_max_age=HSTS_ONE_YEAR, csp="default-src 'self'")
        assert middleware.hsts_max_age == HSTS_ONE_YEAR
        assert middleware.csp == "default-src 'self'"

    @pytest.mark.asyncio
    async def test_dispatch_adds_security_headers(
        self, mock_app: FastAPI, mock_request: Request, mock_response: Response
    ) -> None:
        """Test that dispatch adds all security headers to the response."""
        middleware = SecurityHeadersMiddleware(mock_app, hsts_max_age=HSTS_ONE_YEAR, csp="default-src 'self'")

        call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, call_next)

        assert result == mock_response
        assert result.headers["Strict-Transport-Security"] == f"max-age={HSTS_ONE_YEAR}; includeSubDomains"
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["Content-Security-Policy"] == "default-src 'self'"
        assert result.headers["X-XSS-Protection"] == "1; mode=block"
        assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
