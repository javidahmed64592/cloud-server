"""Unit tests for the cloud_server.server module."""

from collections.abc import Generator
from importlib.metadata import PackageMetadata
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from cloud_server.db import FilesMetadataDatabaseManager
from cloud_server.models import CloudServerConfig
from cloud_server.routers import FilesRouter
from cloud_server.server import CloudServer


@pytest.fixture(autouse=True)
def mock_package_metadata() -> Generator[MagicMock]:
    """Mock importlib.metadata.metadata to return a mock PackageMetadata."""
    with patch("python_template_server.template_server.metadata") as mock_metadata:
        mock_pkg_metadata = MagicMock(spec=PackageMetadata)
        metadata_dict = {
            "Name": "cloud-server",
            "Version": "0.1.0",
            "Summary": "A FastAPI-based local cloud server.",
        }
        mock_pkg_metadata.__getitem__.side_effect = lambda key: metadata_dict[key]
        mock_metadata.return_value = mock_pkg_metadata
        yield mock_metadata


@pytest.fixture
def mock_server(
    mock_cloud_server_config: CloudServerConfig,
    mock_files_metadata_database_manager: FilesMetadataDatabaseManager,
    mock_files_router: FilesRouter,
    mock_tmp_server_path: Path,
    mock_tmp_storage_path: Path,
) -> Generator[CloudServer]:
    """Provide a CloudServer instance for testing."""
    with (
        patch("cloud_server.server.CloudServerConfig.save_to_file"),
        patch("cloud_server.server.FilesMetadataDatabaseManager", return_value=mock_files_metadata_database_manager),
        patch("cloud_server.server.FilesRouter", return_value=mock_files_router),
        patch.object(CloudServer, "server_directory", new_callable=PropertyMock, return_value=mock_tmp_server_path),
        patch.object(CloudServer, "storage_directory", new_callable=PropertyMock, return_value=mock_tmp_storage_path),
    ):
        server = CloudServer(config=mock_cloud_server_config)
        yield server


class TestCloudServer:
    """Unit tests for the CloudServer class."""

    def test_init(self, mock_server: CloudServer, mock_files_router: FilesRouter) -> None:
        """Test CloudServer initialization."""
        assert isinstance(mock_server.config, CloudServerConfig)
        for route in [
            *mock_files_router.router.routes,
        ]:
            assert route in mock_server.app.routes
        assert isinstance(mock_server.files_metadata_database_manager, FilesMetadataDatabaseManager)
        assert mock_server.server_directory.exists()
        assert mock_server.storage_directory.exists()

    def test_validate_config(self, mock_server: CloudServer, mock_cloud_server_config: CloudServerConfig) -> None:
        """Test configuration validation."""
        config_dict = mock_cloud_server_config.model_dump()
        validated_config = mock_server.validate_config(config_dict)
        assert validated_config == mock_cloud_server_config

    def test_validate_config_invalid_returns_default(self, mock_server: CloudServer) -> None:
        """Test invalid configuration returns default configuration."""
        invalid_config = {"model": None}
        validated_config = mock_server.validate_config(invalid_config)
        assert isinstance(validated_config, CloudServerConfig)
