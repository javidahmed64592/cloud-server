"""Unit tests for the python_template_server.routers.template_server_router module."""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.routing import APIRoute

from python_template_server.routers import TemplateServerRouter


class TestRoutes:
    """Unit tests for route setup in TemplateServerRouter."""

    def test_setup_routes(self, mock_template_server_router: TemplateServerRouter) -> None:
        """Test that routes are set up correctly."""
        api_routes = [route for route in mock_template_server_router.router.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        expected_endpoints = [
            "/health",
            "/login",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in routes


class TestGetHealthEndpoint:
    """Integration tests for the /health endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_get_health(self, mock_template_server_router: TemplateServerRouter, mock_request_object: Request) -> None:
        """Test the /health endpoint method."""
        response = asyncio.run(mock_template_server_router.get_health(mock_request_object))
        assert response.message == "Server is healthy"
        assert isinstance(response.timestamp, str)


class TestGetLoginEndpoint:
    """Integration tests for the /login endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_get_login(self, mock_template_server_router: TemplateServerRouter, mock_request_object: Request) -> None:
        """Test the /login endpoint method."""
        response = asyncio.run(mock_template_server_router.get_login(mock_request_object))
        assert response.message == "Login successful."
        assert isinstance(response.timestamp, str)
