"""Pytest fixtures for the application's unit tests."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from slowapi import Limiter

from python_template_server.models import (
    CertificateConfigModel,
    CORSConfigModel,
    DatabaseConfig,
    JSONResponseConfigModel,
    RateLimitConfigModel,
    SecurityConfigModel,
    TemplateServerConfig,
)
from python_template_server.routers.template_server_router import TemplateServerRouter
from python_template_server.template_server import TEMPLATE_SERVER_ROUTER


# General fixtures
@pytest.fixture
def mock_exists() -> Generator[MagicMock]:
    """Mock the Path.exists() method."""
    with patch("pathlib.Path.exists") as mock_exists:
        yield mock_exists


@pytest.fixture
def mock_mkdir() -> Generator[MagicMock]:
    """Mock Path.mkdir method."""
    with patch("pathlib.Path.mkdir") as mock_mkdir:
        yield mock_mkdir


@pytest.fixture
def mock_touch() -> Generator[MagicMock]:
    """Mock the Path.touch() method."""
    with patch("pathlib.Path.touch") as mock_touch:
        yield mock_touch


@pytest.fixture
def mock_read_text() -> Generator[MagicMock]:
    """Mock the Path.read_text() method."""
    with patch("pathlib.Path.read_text") as mock_read:
        yield mock_read


@pytest.fixture
def mock_write_text() -> Generator[MagicMock]:
    """Mock the Path.write_text() method."""
    with patch("pathlib.Path.write_text") as mock_write:
        yield mock_write


@pytest.fixture
def mock_tmp_config_path(tmp_path: Path) -> Path:
    """Provide a temporary config file path."""
    return tmp_path / "config.json"


@pytest.fixture
def mock_tmp_static_path(tmp_path: Path) -> Path:
    """Provide a temporary static file path."""
    return tmp_path / "static"


@pytest.fixture
def mock_tmp_db_path(tmp_path: Path) -> Path:
    """Provide a temporary database directory path."""
    return tmp_path / "data"


# Template Server Configuration Models
@pytest.fixture
def mock_security_config_dict() -> dict:
    """Provide a mock security configuration dictionary."""
    return {
        "hsts_max_age": 31536000,
        "content_security_policy": "default-src 'self'",
    }


@pytest.fixture
def mock_cors_config_dict() -> dict:
    """Provide a mock CORS configuration dictionary."""
    return {
        "enabled": True,
        "allow_origins": ["https://example.com"],
        "allow_credentials": True,
        "allow_methods": ["GET"],
        "allow_headers": ["Content-Type", "X-API-Key"],
        "expose_headers": ["X-Custom-Header"],
        "max_age": 600,
    }


@pytest.fixture
def mock_rate_limit_config_dict() -> dict:
    """Provide a mock rate limit configuration dictionary."""
    return {
        "enabled": False,
        "rate_limit": "200/minute",
        "storage_uri": "memory://",
    }


@pytest.fixture
def mock_certificate_config_dict() -> dict:
    """Provide a mock certificate configuration dictionary."""
    return {
        "directory": "/path/to/certs",
        "ssl_keyfile": "key.pem",
        "ssl_certfile": "cert.pem",
        "days_valid": 365,
    }


@pytest.fixture
def mock_json_response_config_dict() -> dict:
    """Provide a mock JSON response configuration dictionary."""
    return {
        "ensure_ascii": False,
        "allow_nan": False,
        "indent": None,
        "media_type": "application/json; charset=utf-8",
    }


@pytest.fixture
def mock_db_config_dict(mock_tmp_db_path: Path) -> dict:
    """Provide a mock database configuration dictionary."""
    return {
        "db_directory": mock_tmp_db_path,
    }


@pytest.fixture
def mock_security_config(mock_security_config_dict: dict) -> SecurityConfigModel:
    """Provide a mock SecurityConfigModel instance."""
    return SecurityConfigModel.model_validate(mock_security_config_dict)


@pytest.fixture
def mock_cors_config(mock_cors_config_dict: dict) -> CORSConfigModel:
    """Provide a mock CORSConfigModel instance."""
    return CORSConfigModel.model_validate(mock_cors_config_dict)


@pytest.fixture
def mock_rate_limit_config(mock_rate_limit_config_dict: dict) -> RateLimitConfigModel:
    """Provide a mock RateLimitConfigModel instance."""
    return RateLimitConfigModel.model_validate(mock_rate_limit_config_dict)


@pytest.fixture
def mock_certificate_config(mock_certificate_config_dict: dict) -> CertificateConfigModel:
    """Provide a mock CertificateConfigModel instance."""
    return CertificateConfigModel.model_validate(mock_certificate_config_dict)


@pytest.fixture
def mock_json_response_config(mock_json_response_config_dict: dict) -> JSONResponseConfigModel:
    """Provide a mock JSONResponseConfigModel instance."""
    return JSONResponseConfigModel.model_validate(mock_json_response_config_dict)


@pytest.fixture
def mock_db_config(mock_db_config_dict: dict) -> DatabaseConfig:
    """Provide a mock DatabaseConfig instance."""
    return DatabaseConfig.model_validate(mock_db_config_dict)


@pytest.fixture
def mock_template_server_config(
    mock_security_config: SecurityConfigModel,
    mock_cors_config: CORSConfigModel,
    mock_rate_limit_config: RateLimitConfigModel,
    mock_certificate_config: CertificateConfigModel,
    mock_json_response_config: JSONResponseConfigModel,
) -> TemplateServerConfig:
    """Provide a mock TemplateServerConfig instance."""
    return TemplateServerConfig(
        security=mock_security_config,
        cors=mock_cors_config,
        rate_limit=mock_rate_limit_config,
        certificate=mock_certificate_config,
        json_response=mock_json_response_config,
    )


# Server fixtures
@pytest.fixture(autouse=True)
def mock_limiter() -> Limiter:
    """Provide a mock Limiter instance for testing."""
    mock_limiter = MagicMock(spec=Limiter)
    mock_limiter.limit.return_value = MagicMock(return_value=MagicMock())
    return mock_limiter


@pytest.fixture
def mock_template_server_router(mock_limiter: Limiter) -> TemplateServerRouter:
    """Provide a TemplateServerRouter instance for testing."""
    TEMPLATE_SERVER_ROUTER.configure(
        hashed_token="hashed_value",  # noqa: S106
        limiter=mock_limiter,
        rate_limit="10/minute",
    )
    TEMPLATE_SERVER_ROUTER.setup_routes()
    return TEMPLATE_SERVER_ROUTER
