"""Pytest fixtures for the application's unit tests."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from PIL import Image
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
from cloud_server.thumbnail_generator import ThumbnailGenerator

rng = np.random.default_rng()


# General fixtures
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


@pytest.fixture
def mock_tmp_thumbnails_path(mock_tmp_storage_path: Path) -> Path:
    """Provide a temporary thumbnails directory path."""
    return mock_tmp_storage_path / ".thumbnails"


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
        "thumbnail_size": (10, 10),
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
    mock_image_metadata: FileMetadata,
    mock_video_metadata: FileMetadata,
) -> Generator[FilesMetadataDatabaseManager]:
    """Provide a FilesMetadataDatabaseManager instance for testing."""
    db_manager = FilesMetadataDatabaseManager()
    db_manager.configure(db_config=mock_db_config)
    pooled_engine = db_manager.engine
    db_manager.engine = create_engine(pooled_engine.url, poolclass=NullPool)
    pooled_engine.dispose()
    db_manager.perform_file_metadata_action(DatabaseAction.CREATE, file_metadata=mock_file_metadata)
    db_manager.perform_file_metadata_action(DatabaseAction.CREATE, file_metadata=mock_image_metadata)
    db_manager.perform_file_metadata_action(DatabaseAction.CREATE, file_metadata=mock_video_metadata)
    yield db_manager
    db_manager.engine.dispose()


# File Models
@pytest.fixture
def mock_text_file(mock_tmp_storage_path: Path) -> Path:
    """Create a mock text file in the storage directory."""
    text_file = mock_tmp_storage_path / "test_file.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text("fake text data")
    return text_file


@pytest.fixture
def mock_image_file(mock_tmp_storage_path: Path, mock_storage_config: StorageConfig) -> Path:
    """Create a mock image file in the storage directory."""
    image_file = mock_tmp_storage_path / "test_image.jpg"
    image_file.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", mock_storage_config.thumbnail_size, color=(255, 0, 0))
    img.save(image_file, format="JPEG")
    return image_file


@pytest.fixture
def mock_video_file(
    mock_tmp_storage_path: Path, mock_storage_config: StorageConfig, mock_image_array: np.ndarray
) -> Path:
    """Create a mock video file in the storage directory."""
    video_file = mock_tmp_storage_path / "test_video.mp4"
    video_file.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
    out = cv2.VideoWriter(str(video_file), fourcc, 30.0, mock_storage_config.thumbnail_size)

    for _ in range(10):
        out.write(mock_image_array)

    out.release()
    return video_file


@pytest.fixture
def mock_file_metadata(mock_text_file: Path) -> FileMetadata:
    """Provide a mock FileMetadata instance."""
    return FileMetadata(
        id=None,
        filename=mock_text_file.name,
        parent_directory=Path("."),
        mime_type="text/plain",
        size=1024,
    )


@pytest.fixture
def mock_image_metadata(mock_image_file: Path) -> FileMetadata:
    """Provide a FileMetadata instance for a mock image file."""
    return FileMetadata(
        id=None,
        filename=mock_image_file.name,
        parent_directory=Path("."),
        mime_type="image/jpeg",
        size=1024,
    )


@pytest.fixture
def mock_video_metadata(mock_video_file: Path) -> FileMetadata:
    """Provide a FileMetadata instance for a mock video file."""
    return FileMetadata(
        id=None,
        filename=mock_video_file.name,
        parent_directory=Path("."),
        mime_type="video/mp4",
        size=2048,
    )


# Thumbnail fixtures
@pytest.fixture
def mock_image_array(mock_storage_config: StorageConfig) -> np.ndarray:
    """Provide a mock image array for video thumbnail generation."""
    return rng.integers(0, 256, (*mock_storage_config.thumbnail_size, 3), dtype=np.uint8)


@pytest.fixture
def mock_image(mock_storage_config: StorageConfig) -> Image.Image:
    """Mock image."""
    mock_img = MagicMock(spec=Image.Image)
    mock_img.copy.return_value = mock_img
    mock_img.mode = "RGB"
    mock_img.size = mock_storage_config.thumbnail_size
    mock_img.convert.return_value = mock_img
    mock_img.thumbnail = MagicMock()

    def mock_save(path: Path, *args: object, **kwargs: object) -> None:
        """Create a file when save is called."""
        Path(path).touch()

    mock_img.save = mock_save
    return mock_img


@pytest.fixture
def mock_image_open(mock_image: Image.Image) -> Generator[MagicMock]:
    """Mock PIL.Image.open to return a mock image."""
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_image
    mock_context.__exit__.return_value = None

    with patch("PIL.Image.open", return_value=mock_context) as mock_open:
        yield mock_open


@pytest.fixture
def mock_image_fromarray(mock_image: Image.Image) -> Generator[MagicMock]:
    """Mock PIL.Image.fromarray to return a mock image."""
    with patch("PIL.Image.fromarray", return_value=mock_image) as mock_fromarray:
        yield mock_fromarray


@pytest.fixture
def mock_video_capture(mock_image_array: np.ndarray) -> Generator[MagicMock]:
    """Mock cv2.VideoCapture for video thumbnail generation."""
    mock_video = MagicMock()
    mock_video.isOpened.return_value = True
    mock_video.get.return_value = 30.0
    mock_video.read.return_value = (True, mock_image_array)

    with patch("cv2.VideoCapture", return_value=mock_video) as mock_cap:
        yield mock_cap


@pytest.fixture
def mock_cv2_cvtcolor(mock_image_array: np.ndarray) -> Generator[MagicMock]:
    """Mock cv2.cvtColor for color conversion."""
    with patch("cv2.cvtColor", return_value=mock_image_array) as mock_cvt:
        yield mock_cvt


@pytest.fixture
def mock_thumbnail_generator(mock_tmp_thumbnails_path: Path) -> ThumbnailGenerator:
    """Provide a ThumbnailGenerator instance for testing."""
    return ThumbnailGenerator(thumbnails_directory=mock_tmp_thumbnails_path)


# Server fixtures
@pytest.fixture(autouse=True)
def mock_limiter() -> Limiter:
    """Provide a mock Limiter instance for testing."""
    mock_limiter = MagicMock(spec=Limiter)
    mock_limiter.limit.return_value = MagicMock(return_value=MagicMock())
    return mock_limiter


@pytest.fixture
def mock_files_router(
    mock_limiter: Limiter,
    mock_files_metadata_database_manager: FilesMetadataDatabaseManager,
    mock_tmp_storage_path: Path,
    mock_storage_config: StorageConfig,
    mock_thumbnail_generator: ThumbnailGenerator,
) -> FilesRouter:
    """Provide a FilesRouter instance for testing."""
    FILES_ROUTER.configure(
        hashed_token="hashed_value",  # noqa: S106
        limiter=mock_limiter,
        rate_limit="10/minute",
    )
    FILES_ROUTER.setup_routes()
    FILES_ROUTER.configure_router(
        db=mock_files_metadata_database_manager,
        storage_directory=mock_tmp_storage_path,
        storage_config=mock_storage_config,
        thumbnail_generator=mock_thumbnail_generator,
    )
    return FILES_ROUTER
