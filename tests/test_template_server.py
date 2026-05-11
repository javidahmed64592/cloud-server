"""Unit tests for the python_template_server.template_server module."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Generator
from importlib.metadata import PackageMetadata
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from python_template_server.constants import API_PREFIX
from python_template_server.main import ExampleServer
from python_template_server.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from python_template_server.models import (
    CustomJSONResponse,
    ResponseCode,
    TemplateServerConfig,
)
from python_template_server.routers.template_server_router import TemplateServerRouter
from python_template_server.template_server import TemplateServer


@pytest.fixture(autouse=True)
def mock_package_metadata() -> Generator[PackageMetadata]:
    """Mock importlib.metadata.metadata to return a mock PackageMetadata."""
    with patch("python_template_server.template_server.metadata") as mock_metadata:
        mock_pkg_metadata = MagicMock(spec=PackageMetadata)
        metadata_dict = {
            "Name": "python-template-server",
            "Version": "0.1.3",
            "Summary": "A template FastAPI server with production-ready configuration.",
        }
        mock_pkg_metadata.__getitem__.side_effect = lambda key: metadata_dict[key]
        mock_metadata.return_value = mock_pkg_metadata
        yield mock_metadata


MOCK_INDEX_CONTENT = "<html><body><h1>Test SPA</h1></body></html>"
MOCK_NOT_FOUND_CONTENT = "<html><body><h1>404 Not Found</h1></body></html>"
MOCK_DIRECTORY_INDEX_CONTENT = "<html><body><h1>Directory Index</h1></body></html>"


@pytest.fixture
def mock_template_server(
    mock_template_server_config: TemplateServerConfig,
    mock_tmp_config_path: Path,
    mock_tmp_static_path: Path,
    mock_template_server_router: TemplateServerRouter,
) -> Generator[TemplateServer]:
    """Provide a ExampleServer instance for testing."""
    with (
        patch("python_template_server.template_server.CertificateHandler", return_value=MagicMock(), autospec=True),
        patch(
            "python_template_server.template_server.TemplateServerRouter",
            return_value=mock_template_server_router,
            autospec=True,
        ),
    ):
        mock_tmp_static_path.mkdir(parents=True, exist_ok=True)
        (mock_tmp_static_path / "index.html").write_text(MOCK_INDEX_CONTENT)
        (mock_tmp_static_path / "404.html").write_text(MOCK_NOT_FOUND_CONTENT)

        (mock_tmp_static_path / "directory").mkdir(parents=True, exist_ok=True)
        (mock_tmp_static_path / "directory" / "index.html").write_text(MOCK_DIRECTORY_INDEX_CONTENT)
        yield ExampleServer(
            config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path, config=mock_template_server_config
        )


@pytest.fixture
def mock_client(mock_template_server: TemplateServer) -> TestClient:
    """Provide a TestClient for the mock server."""
    return TestClient(mock_template_server.app)


class TestTemplateServer:
    """Unit tests for the TemplateServer class."""

    def test_init(
        self, mock_template_server: TemplateServer, mock_template_server_router: TemplateServerRouter
    ) -> None:
        """Test TemplateServer initialization."""
        assert isinstance(mock_template_server.app, FastAPI)
        assert mock_template_server.app.title == mock_template_server.package_metadata["Name"]
        assert mock_template_server.app.description == mock_template_server.package_metadata["Summary"]
        assert mock_template_server.app.version == mock_template_server.package_metadata["Version"]
        assert mock_template_server.app.root_path == API_PREFIX
        assert isinstance(mock_template_server.api_key_header, APIKeyHeader)
        for route in mock_template_server_router.router.routes:
            assert route in mock_template_server.app.routes

    def test_init_token_hash_not_set(
        self, mock_template_server_config: TemplateServerConfig, mock_tmp_config_path: Path, mock_tmp_static_path: Path
    ) -> None:
        """Test initialization when token is not configured."""
        with (
            patch.dict(os.environ, {"API_TOKEN_HASH": ""}),
            pytest.raises(HTTPException, match=f"{ResponseCode.INTERNAL_SERVER_ERROR}: Server token is not configured"),
        ):
            ExampleServer(
                config_filepath=mock_tmp_config_path,
                static_dir=mock_tmp_static_path,
                config=mock_template_server_config,
            )

    def test_request_middleware_added(self, mock_template_server: TemplateServer) -> None:
        """Test that all middleware is added to the app."""
        middlewares = [middleware.cls for middleware in mock_template_server.app.user_middleware]
        assert RequestLoggingMiddleware in middlewares
        assert SecurityHeadersMiddleware in middlewares

    def test_cors_middleware_added_when_enabled(
        self, mock_template_server_config: TemplateServerConfig, mock_tmp_config_path: Path, mock_tmp_static_path: Path
    ) -> None:
        """Test that CORS middleware is added when enabled."""
        mock_template_server_config.cors.enabled = True
        server = ExampleServer(
            config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path, config=mock_template_server_config
        )

        middlewares = [middleware.cls for middleware in server.app.user_middleware]
        assert CORSMiddleware in middlewares

    def test_cors_middleware_not_added_when_disabled(
        self, mock_template_server_config: TemplateServerConfig, mock_tmp_config_path: Path, mock_tmp_static_path: Path
    ) -> None:
        """Test that CORS middleware is not added when disabled."""
        mock_template_server_config.cors.enabled = False
        server = ExampleServer(
            config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path, config=mock_template_server_config
        )

        middlewares = [middleware.cls for middleware in server.app.user_middleware]
        assert CORSMiddleware not in middlewares

    def test_json_response_configured(self, mock_template_server_config: TemplateServerConfig) -> None:
        """Test that CustomJSONResponse is properly configured during initialization."""
        # Verify CustomJSONResponse class variables are set correctly
        assert CustomJSONResponse._ensure_ascii == mock_template_server_config.json_response.ensure_ascii
        assert CustomJSONResponse._allow_nan == mock_template_server_config.json_response.allow_nan
        assert CustomJSONResponse._indent == mock_template_server_config.json_response.indent
        assert CustomJSONResponse.media_type == mock_template_server_config.json_response.media_type

        # Test that CustomJSONResponse renders correctly with configured settings
        response = CustomJSONResponse(content={"test": "data", "emoji": "👋"})
        rendered = response.render({"test": "data", "emoji": "👋"})

        # With ensure_ascii=False, emojis should be preserved
        assert "👋".encode() in rendered
        assert b'"test":"data"' in rendered  # Compact format (no spaces)


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_config_with_filepath_success(
        self, mock_template_server_config: TemplateServerConfig, mock_tmp_config_path: Path, mock_tmp_static_path: Path
    ) -> None:
        """Test that load_config is called with the specified filepath when config is None."""
        with patch.object(ExampleServer, "load_config", return_value=mock_template_server_config) as mock_load_config:
            server = ExampleServer(config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path)

            mock_load_config.assert_called_once_with(mock_tmp_config_path)
            assert server.config == mock_template_server_config

    def test_load_config_file_not_found(
        self, mock_exists: MagicMock, mock_tmp_config_path: Path, mock_tmp_static_path: Path
    ) -> None:
        """Test loading config when the file does not exist."""
        mock_exists.return_value = False

        with pytest.raises(SystemExit):
            ExampleServer(config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path)

    def test_load_config_invalid_json(
        self,
        mock_exists: MagicMock,
        mock_read_text: MagicMock,
        mock_tmp_config_path: Path,
        mock_tmp_static_path: Path,
    ) -> None:
        """Test loading config with invalid JSON content."""
        mock_exists.return_value = True
        mock_read_text.return_value = "invalid json"

        with pytest.raises(SystemExit):
            ExampleServer(config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path)

    def test_load_config_os_error(
        self,
        mock_exists: MagicMock,
        mock_read_text: MagicMock,
        mock_tmp_config_path: Path,
        mock_tmp_static_path: Path,
    ) -> None:
        """Test loading config that raises an OSError."""
        mock_exists.return_value = True
        mock_read_text.side_effect = OSError("File read error")

        with pytest.raises(SystemExit):
            ExampleServer(config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path)

    def test_load_config_validation_error(
        self,
        mock_exists: MagicMock,
        mock_read_text: MagicMock,
        mock_tmp_config_path: Path,
        mock_tmp_static_path: Path,
    ) -> None:
        """Test loading config that fails validation."""
        mock_exists.return_value = True
        mock_read_text.return_value = json.dumps({"security": {"hsts_max_age": -1}})

        with pytest.raises(SystemExit):
            ExampleServer(config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path)


class TestRateLimiting:
    """Unit tests for rate limiting functionality."""

    def test_rate_limit_exception_handler(self, mock_template_server: TemplateServer) -> None:
        """Test that _rate_limit_exception_handler increments counter and returns expected response."""
        request = MagicMock(spec=Request)

        # Use a mock exception with retry_after attribute to avoid constructor requirement
        exc = MagicMock(spec=RateLimitExceeded)
        exc.retry_after = 42

        # Call the handler
        response = asyncio.run(mock_template_server._rate_limit_exception_handler(request, exc))

        # Verify JSONResponse status and content
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        assert isinstance(response.body, bytes)
        assert json.loads(response.body.decode()) == {"detail": "Rate limit exceeded"}
        assert response.headers.get("Retry-After") == str(exc.retry_after)

    def test_setup_rate_limiting_enabled(
        self, mock_template_server_config: TemplateServerConfig, mock_tmp_config_path: Path, mock_tmp_static_path: Path
    ) -> None:
        """Test rate limiting setup when enabled."""
        mock_template_server_config.rate_limit.enabled = True

        server = ExampleServer(
            config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path, config=mock_template_server_config
        )

        assert server.limiter is not None
        assert server.app.state.limiter is not None

    def test_setup_rate_limiting_disabled(
        self, mock_template_server_config: TemplateServerConfig, mock_tmp_config_path: Path, mock_tmp_static_path: Path
    ) -> None:
        """Test rate limiting setup when disabled."""
        server = ExampleServer(
            config_filepath=mock_tmp_config_path, static_dir=mock_tmp_static_path, config=mock_template_server_config
        )

        assert server.limiter is None


class TestServeSPA:
    """Tests for the SPA serving functionality."""

    def test_serve_spa_endpoint(self, mock_client: TestClient) -> None:
        """Test SPA serving endpoint returns static file."""
        response = mock_client.get("index.html")
        assert response.status_code == ResponseCode.OK
        assert response.content.decode() == MOCK_INDEX_CONTENT

    def test_serve_spa_directory_index(self, mock_client: TestClient) -> None:
        """Test SPA serving endpoint returns directory index file."""
        response = mock_client.get("/directory/")
        assert response.status_code == ResponseCode.OK
        assert response.content.decode() == MOCK_DIRECTORY_INDEX_CONTENT

    def test_serve_spa_endpoint_404_redirect(self, mock_client: TestClient) -> None:
        """Test SPA serving endpoint returns custom 404 page."""
        response = mock_client.get("/nonexistent-page")
        assert response.status_code == ResponseCode.NOT_FOUND
        assert response.content.decode() == MOCK_NOT_FOUND_CONTENT


class TestTemplateServerRun:
    """Unit tests for TemplateServer.run method."""

    @pytest.fixture
    def mock_uvicorn_run(self) -> Generator[MagicMock]:
        """Mock uvicorn.run function."""
        with patch("python_template_server.template_server.uvicorn.run") as mock_run:
            yield mock_run

    def test_run_success(
        self, mock_template_server: TemplateServer, mock_exists: MagicMock, mock_uvicorn_run: MagicMock
    ) -> None:
        """Test successful server run."""
        mock_exists.side_effect = [True, True]

        mock_template_server.run()

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args.kwargs
        assert call_kwargs["app"] == mock_template_server.app
        assert call_kwargs["host"] == mock_template_server.host
        assert call_kwargs["port"] == mock_template_server.port

    def test_run_generates_cert_when_missing(
        self, mock_template_server: TemplateServer, mock_exists: MagicMock, mock_uvicorn_run: MagicMock
    ) -> None:
        """Test that self-signed certificate is generated when cert/key files are missing."""
        # Mock the cert and key file paths to not exist
        mock_exists.side_effect = [False, False]

        mock_template_server.run()

        mock_template_server.cert_handler.generate_self_signed_cert.assert_called_once()  # type: ignore[attr-defined]
        mock_uvicorn_run.assert_called_once()

    def test_run_error(
        self, mock_template_server: TemplateServer, mock_exists: MagicMock, mock_uvicorn_run: MagicMock
    ) -> None:
        """Test run raises SystemExit on Exception."""
        mock_exists.side_effect = [True, True]

        mock_uvicorn_run.side_effect = Exception("Test Exception")

        with pytest.raises(SystemExit):
            mock_template_server.run()
