"""Pytest fixtures for the application's unit tests."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from slowapi import Limiter
from sqlalchemy import NullPool, create_engine

from cloud_server.db import FilesMetadataDatabaseManager
from cloud_server.models import (
    CloudServerConfig,
    DatabaseAction,
    FileMetadata,
    ServerDatabaseConfig,
    StorageConfig,
)
from cloud_server.routers.files_router import FilesRouter
from cloud_server.server import FILES_ROUTER


# General fixtures
@pytest.fixture
def mock_tmp_config_path(tmp_path: Path) -> Path:
    """Provide a temporary config file path."""
    return tmp_path / "config.json"


@pytest.fixture
def mock_tmp_db_path(tmp_path: Path) -> Path:
    """Provide a temporary database directory path."""
    return tmp_path / "data"


@pytest.fixture
def mock_tmp_server_path(tmp_path: Path) -> Path:
    """Provide a temporary server directory path."""
    return tmp_path / "server"


@pytest.fixture
def mock_tmp_storage_path(mock_tmp_server_path: Path) -> Path:
    """Provide a temporary storage directory path."""
    return mock_tmp_server_path / "storage"


# Cloud Server Configuration Models
@pytest.fixture
def mock_db_config_dict(mock_tmp_db_path: Path) -> dict:
    """Provide a mock database configuration dictionary."""
    return {
        "db_directory": mock_tmp_db_path,
        "files_metadata_db_filename": "files_metadata.db",
    }


@pytest.fixture
def mock_storage_config_dict() -> dict:
    """Provide a mock storage configuration dictionary."""
    return {
        "upload_chunk_size_kb": 8,
        "max_file_size_mb": 100,
    }


@pytest.fixture
def mock_db_config(mock_db_config_dict: dict) -> ServerDatabaseConfig:
    """Provide a mock ServerDatabaseConfig instance."""
    return ServerDatabaseConfig.model_validate(mock_db_config_dict)  # type: ignore[no-any-return]


@pytest.fixture
def mock_storage_config(mock_storage_config_dict: dict) -> StorageConfig:
    """Provide a mock StorageConfig instance."""
    return StorageConfig.model_validate(mock_storage_config_dict)


@pytest.fixture
def mock_cloud_server_config(
    mock_db_config: ServerDatabaseConfig,
    mock_storage_config: StorageConfig,
) -> CloudServerConfig:
    """Provide a mock CloudServerConfig instance."""
    return CloudServerConfig(
        db=mock_db_config,
        storage_config=mock_storage_config,
    )


# Database fixtures
@pytest.fixture
def mock_files_metadata_database_manager(
    mock_db_config: ServerDatabaseConfig,
    mock_file_metadata: FileMetadata,
) -> Generator[FilesMetadataDatabaseManager]:
    """Provide a FilesMetadataDatabaseManager instance for testing."""
    mock_file_metadata.parent_directory.mkdir(parents=True, exist_ok=True)
    mock_file_metadata.filepath.write_text("Test file content")

    db_manager = FilesMetadataDatabaseManager()
    db_manager.configure(db_config=mock_db_config)
    pooled_engine = db_manager.engine
    db_manager.engine = create_engine(pooled_engine.url, poolclass=NullPool)
    pooled_engine.dispose()
    db_manager.perform_file_metadata_action(DatabaseAction.CREATE, file_metadata=mock_file_metadata)
    yield db_manager
    db_manager.engine.dispose()


# File Models
@pytest.fixture
def mock_file_metadata(mock_tmp_storage_path: Path) -> FileMetadata:
    """Provide a mock FileMetadata instance."""
    return FileMetadata(
        id=None,
        filename="test_file.txt",
        parent_directory=mock_tmp_storage_path,
        mime_type="text/plain",
        size=1024,
    )


# Server fixtures
@pytest.fixture(autouse=True)
def mock_limiter() -> Limiter:
    """Provide a mock Limiter instance for testing."""
    mock_limiter = MagicMock(spec=Limiter)
    mock_limiter.limit.return_value = MagicMock(return_value=MagicMock())
    return mock_limiter


@pytest.fixture
def mock_files_router(mock_limiter: Limiter) -> FilesRouter:
    """Provide a FilesRouter instance for testing."""
    FILES_ROUTER.configure(
        hashed_token="hashed_value",  # noqa: S106
        limiter=mock_limiter,
        rate_limit="10/minute",
    )
    FILES_ROUTER.setup_routes()
    return FILES_ROUTER
