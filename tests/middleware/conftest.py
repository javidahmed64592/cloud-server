"""Pytest fixtures for the middleware's unit tests."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request, Response


@pytest.fixture
def mock_app() -> FastAPI:
    """Provide a mock FastAPI app."""
    return MagicMock(spec=FastAPI)


@pytest.fixture
def mock_request() -> Request:
    """Provide a mock Request."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_response() -> Response:
    """Provide a mock Response with headers."""
    response = MagicMock(spec=Response)
    response.headers = {}
    response.status_code = 200
    return response
