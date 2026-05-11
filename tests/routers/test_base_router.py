"""Unit tests for the python_template_server.routers.base_router module."""

import asyncio
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.routing import APIRoute
from slowapi import Limiter

from python_template_server.models import BaseResponse, ResponseCode
from python_template_server.routers import BaseRouter

MOCK_TOKEN = "hashed_value"  # noqa: S105
MOCK_RATE_LIMIT = "10/minute"


class MockRouter(BaseRouter):
    """Mock implementation of BaseRouter for testing."""

    def mock_unprotected_method(self, request: Request) -> BaseResponse:
        """Mock unprotected method."""
        return BaseResponse(message="unprotected endpoint")

    def mock_protected_method(self, request: Request) -> BaseResponse:
        """Mock protected method."""
        return BaseResponse(message="protected endpoint")

    def mock_unlimited_unprotected_method(self, request: Request) -> BaseResponse:
        """Mock unlimited unprotected method."""
        return BaseResponse(message="unlimited unprotected endpoint")

    def mock_unlimited_protected_method(self, request: Request) -> BaseResponse:
        """Mock unlimited protected method."""
        return BaseResponse(message="unlimited protected endpoint")

    def setup_routes(self) -> None:
        """Set up mock routes for testing."""
        mock_limiter = MagicMock(spec=Limiter)
        mock_limiter.limit.return_value = MagicMock(return_value=MagicMock())

        self.configure(hashed_token=MOCK_TOKEN, limiter=mock_limiter, rate_limit=MOCK_RATE_LIMIT)
        self.add_route(
            endpoint="/unauthenticated-endpoint",
            handler_function=self.mock_unprotected_method,
            response_model=BaseResponse,
            methods=["GET"],
            limited=True,
            authentication_required=False,
        )
        self.add_route(
            endpoint="/authenticated-endpoint",
            handler_function=self.mock_protected_method,
            response_model=BaseResponse,
            methods=["POST"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/unlimited-unauthenticated-endpoint",
            handler_function=self.mock_unlimited_unprotected_method,
            response_model=BaseResponse,
            methods=["GET"],
            limited=False,
            authentication_required=False,
        )
        self.add_route(
            endpoint="/unlimited-authenticated-endpoint",
            handler_function=self.mock_unlimited_protected_method,
            response_model=BaseResponse,
            methods=["POST"],
            limited=False,
            authentication_required=True,
        )


@pytest.fixture
def mock_router() -> MockRouter:
    """Fixture to create a mock router instance."""
    router = MockRouter(prefix="/test")
    router.setup_routes()
    return router


@pytest.fixture
def mock_verify_token() -> Generator[MagicMock]:
    """Mock the verify_token function."""
    with patch("python_template_server.routers.base_router.verify_token") as mock_verify:
        yield mock_verify


class TestBaseRouterInitialization:
    """Unit tests for BaseRouter initialization."""

    def test_base_router_initialization(self, mock_router: MockRouter) -> None:
        """Test that the BaseRouter initializes with the correct prefix and default values."""
        assert mock_router.router.prefix == "/test"
        assert mock_router.hashed_token == MOCK_TOKEN


class TestVerifyApiKey:
    """Unit tests for the _verify_api_key method."""

    def test_verify_api_key_valid(self, mock_router: BaseRouter, mock_verify_token: MagicMock) -> None:
        """Test _verify_api_key with valid API key."""
        mock_verify_token.return_value = True

        result = asyncio.run(mock_router._verify_api_key("valid_key"))
        assert result is None

    def test_verify_api_key_missing(self, mock_router: BaseRouter) -> None:
        """Test _verify_api_key with missing API key."""
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_router._verify_api_key(None))

        assert exc_info.value.status_code == ResponseCode.BAD_REQUEST
        assert exc_info.value.detail == "Missing API key"

    def test_verify_api_key_invalid(self, mock_router: BaseRouter, mock_verify_token: MagicMock) -> None:
        """Test _verify_api_key with invalid API key."""
        mock_verify_token.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_router._verify_api_key("invalid_key"))

        assert exc_info.value.status_code == ResponseCode.UNAUTHORIZED
        assert exc_info.value.detail == "Invalid API key"

    def test_verify_api_key_value_error(self, mock_router: BaseRouter, mock_verify_token: MagicMock) -> None:
        """Test _verify_api_key when verify_token raises ValueError."""
        mock_verify_token.side_effect = ValueError("No stored token hash found")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_router._verify_api_key("some_key"))

        assert exc_info.value.status_code == ResponseCode.INTERNAL_SERVER_ERROR
        assert "No stored token hash found" in exc_info.value.detail


class TestConfigure:
    """Unit tests for the configure method."""

    def test_configure(self, mock_router: BaseRouter) -> None:
        """Test that configure sets the hashed_token, limiter, and rate_limit correctly."""
        assert mock_router.hashed_token == MOCK_TOKEN
        assert isinstance(mock_router.limiter, Limiter)
        assert mock_router.rate_limit == MOCK_RATE_LIMIT


class TestAddRoutes:
    """Integration tests for the routes in the mock router."""

    def test_add_unauthenticated_route(self, mock_router: BaseRouter) -> None:
        """Test add_route with authentication disabled adds routes without authentication."""
        api_routes = [route for route in mock_router.router.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        assert "/test/unauthenticated-endpoint" in routes

        # Find the specific route and verify it has no dependencies (unauthenticated)
        test_route = next((route for route in api_routes if route.path == "/test/unauthenticated-endpoint"), None)
        assert test_route is not None

        # Verify the route has no dependencies (unauthenticated)
        assert len(test_route.dependencies) == 0

        # Verify method and response model
        assert "GET" in test_route.methods
        assert test_route.response_model == BaseResponse

    def test_add_authenticated_route(self, mock_router: BaseRouter) -> None:
        """Test add_route with authentication enabled adds routes with authentication."""
        api_routes = [route for route in mock_router.router.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        assert "/test/authenticated-endpoint" in routes

        # Find the specific route
        test_route = next((route for route in api_routes if route.path == "/test/authenticated-endpoint"), None)
        assert test_route is not None

        # Verify the route has dependencies (authentication)
        assert len(test_route.dependencies) > 0
        dependency = test_route.dependencies[0]
        assert dependency.dependency == mock_router._verify_api_key

        # Verify method and response model
        assert "POST" in test_route.methods
        assert test_route.response_model == BaseResponse

    def test_limited_parameter_with_rate_limiting_enabled(self, mock_router: BaseRouter) -> None:
        """Test that limited=True applies rate limiting when limiter is enabled."""
        assert isinstance(mock_router.limiter, Limiter)
        assert mock_router.limiter.limit.call_count == 2  # type: ignore[attr-defined] # noqa: PLR2004
        mock_router.limiter.limit.assert_any_call(MOCK_RATE_LIMIT)  # type: ignore[attr-defined]
