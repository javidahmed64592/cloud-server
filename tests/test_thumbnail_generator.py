"""Unit tests for the cloud_server.thumbnail_generator module."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from cloud_server.models import FileMetadata
from cloud_server.thumbnail_generator import ThumbnailGenerator

rng = np.random.default_rng()


@pytest.fixture
def mock_image() -> Image.Image:
    """Mock image."""
    mock_img = MagicMock(spec=Image.Image)
    mock_img.copy.return_value = mock_img
    mock_img.mode = "RGB"
    mock_img.size = (10, 10)
    mock_img.thumbnail = MagicMock()
    mock_img.save = MagicMock()
    mock_img.convert.return_value = mock_img
    return mock_img


@pytest.fixture
def mock_image_open(mock_image: Image.Image) -> Generator[MagicMock]:
    """Mock PIL.Image.open to return a mock image."""
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_image
    mock_context.__exit__.return_value = None

    with patch("cloud_server.thumbnail_generator.Image.open", return_value=mock_context) as mock_open:
        yield mock_open


@pytest.fixture
def mock_video_capture() -> Generator[MagicMock]:
    """Mock cv2.VideoCapture for video thumbnail generation."""
    mock_video = MagicMock()
    mock_video.isOpened.return_value = True
    mock_video.get.return_value = 30.0  # fps
    mock_video.read.return_value = (True, rng.integers(0, 256, (10, 10, 3), dtype=np.uint8))

    with patch("cloud_server.thumbnail_generator.cv2.VideoCapture", return_value=mock_video) as mock_cap:
        yield mock_cap


@pytest.fixture
def mock_cv2_cvtcolor() -> Generator[MagicMock]:
    """Mock cv2.cvtColor for color conversion."""
    with patch(
        "cloud_server.thumbnail_generator.cv2.cvtColor",
        return_value=rng.integers(0, 256, (10, 10, 3), dtype=np.uint8),
    ) as mock_cvt:
        yield mock_cvt


@pytest.fixture
def mock_image_fromarray(mock_image: Image.Image) -> Generator[MagicMock]:
    """Mock PIL.Image.fromarray to return a mock image."""
    with patch("cloud_server.thumbnail_generator.Image.fromarray", return_value=mock_image) as mock_from:
        yield mock_from


@pytest.fixture
def mock_image_file(mock_tmp_storage_path: Path) -> Path:
    """Create a mock image file in the storage directory."""
    image_file = mock_tmp_storage_path / "test_image.jpg"
    image_file.parent.mkdir(parents=True, exist_ok=True)
    image_file.write_text("fake image data")
    return image_file


@pytest.fixture
def mock_video_file(mock_tmp_storage_path: Path) -> Path:
    """Create a mock video file in the storage directory."""
    video_file = mock_tmp_storage_path / "test_video.mp4"
    video_file.parent.mkdir(parents=True, exist_ok=True)
    video_file.write_text("fake video data")
    return video_file


@pytest.fixture
def mock_image_metadata(mock_image_file: Path) -> FileMetadata:
    """Provide a FileMetadata instance for a mock image file."""
    return FileMetadata(
        id=1,
        filename=mock_image_file.name,
        parent_directory=Path("."),
        mime_type="image/jpeg",
        size=1024,
    )


@pytest.fixture
def mock_video_metadata(mock_video_file: Path) -> FileMetadata:
    """Provide a FileMetadata instance for a mock video file."""
    return FileMetadata(
        id=2,
        filename=mock_video_file.name,
        parent_directory=Path("."),
        mime_type="video/mp4",
        size=2048,
    )


class TestThumbnailGenerator:
    """Unit tests for the ThumbnailGenerator class."""

    def test_init(self, mock_thumbnail_generator: ThumbnailGenerator) -> None:
        """Test ThumbnailGenerator initialization."""
        assert mock_thumbnail_generator._thumbnails_directory.exists()

    def test_thumbnail_path(self, mock_thumbnail_generator: ThumbnailGenerator) -> None:
        """Test thumbnail path generation."""
        file_id = 123
        expected_path = mock_thumbnail_generator._thumbnails_directory / f"{file_id}.jpg"
        assert mock_thumbnail_generator._thumbnail_path(file_id=file_id) == expected_path
        assert mock_thumbnail_generator.get_thumbnail_path(file_id=file_id) == expected_path

    def test_generate_image_thumbnail(
        self,
        mock_thumbnail_generator: ThumbnailGenerator,
        mock_image_file: Path,
        mock_image_open: MagicMock,
        mock_image: Image.Image,
    ) -> None:
        """Test image thumbnail generation."""
        thumbnail_img = mock_thumbnail_generator._generate_image_thumbnail(mock_image_file)
        mock_image_open.assert_called_once_with(mock_image_file)
        mock_image.copy.assert_called_once()  # type: ignore[attr-defined]
        assert thumbnail_img == mock_image

    def test_generate_video_thumbnail(
        self,
        mock_thumbnail_generator: ThumbnailGenerator,
        mock_video_file: Path,
        mock_image: Image.Image,
        mock_video_capture: MagicMock,
        mock_cv2_cvtcolor: MagicMock,
        mock_image_fromarray: MagicMock,
    ) -> None:
        """Test video thumbnail generation."""
        thumbnail_img = mock_thumbnail_generator._generate_video_thumbnail(mock_video_file)
        mock_video_capture.return_value.set.assert_called_once_with(1, 30)  # CAP_PROP_POS_FRAMES
        assert thumbnail_img == mock_image

    def test_generate_thumbnail(
        self,
        mock_thumbnail_generator: ThumbnailGenerator,
        mock_image_file: Path,
        mock_image_open: MagicMock,
        mock_image: Image.Image,
    ) -> None:
        """Test public generate_thumbnail method saves thumbnail to correct location."""
        file_id = 1
        thumbnail_size = (128, 128)
        expected_path = mock_thumbnail_generator._thumbnail_path(file_id=file_id)

        mock_thumbnail_generator.generate_thumbnail(
            filepath=mock_image_file,
            mime_type="image/jpeg",
            file_id=file_id,
            thumbnail_size=thumbnail_size,
        )

        mock_image_open.assert_called_once_with(mock_image_file)
        mock_image.thumbnail.assert_called_once_with(thumbnail_size, Image.Resampling.LANCZOS)  # type: ignore[attr-defined]
        mock_image.save.assert_called_once_with(expected_path, "JPEG", quality=85, optimize=True)  # type: ignore[attr-defined]

    def test_synchronize_with_storage(
        self,
        mock_thumbnail_generator: ThumbnailGenerator,
        mock_tmp_storage_path: Path,
        mock_image_metadata: FileMetadata,
        mock_video_metadata: FileMetadata,
        mock_image_file: Path,
        mock_video_file: Path,
        mock_image_open: MagicMock,
        mock_image: Image.Image,
        mock_video_capture: MagicMock,
        mock_cv2_cvtcolor: MagicMock,
        mock_image_fromarray: MagicMock,
    ) -> None:
        """Test synchronize_with_storage generates thumbnails for image and video files."""
        files_metadata = [mock_image_metadata, mock_video_metadata]
        thumbnail_size = (128, 128)
        expected_thumbnail_count = len(files_metadata)

        mock_thumbnail_generator.synchronize_with_storage(
            storage_directory=mock_tmp_storage_path,
            files_metadata=files_metadata,
            thumbnail_size=thumbnail_size,
        )

        # Verify thumbnail and save were called for both files
        assert mock_image.save.call_count == expected_thumbnail_count  # type: ignore[attr-defined]
        assert mock_image.thumbnail.call_count == expected_thumbnail_count  # type: ignore[attr-defined]
