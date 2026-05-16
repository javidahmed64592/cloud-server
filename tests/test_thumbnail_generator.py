"""Unit tests for the cloud_server.thumbnail_generator module."""

from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

from cloud_server.models import FileMetadata
from cloud_server.thumbnail_generator import ThumbnailGenerator


class TestThumbnailGenerator:
    """Unit tests for the ThumbnailGenerator class."""

    def test_init(self, mock_thumbnail_generator: ThumbnailGenerator) -> None:
        """Test ThumbnailGenerator initialization."""
        assert mock_thumbnail_generator._thumbnails_directory.exists()

    def test_thumbnail_path(self, mock_thumbnail_generator: ThumbnailGenerator) -> None:
        """Test thumbnail path generation."""
        file_id = 123
        expected_path = mock_thumbnail_generator._thumbnails_directory / f"{file_id}.jpg"
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
        expected_path = mock_thumbnail_generator.get_thumbnail_path(file_id=file_id)

        mock_thumbnail_generator.generate_thumbnail(
            filepath=mock_image_file,
            mime_type="image/jpeg",
            file_id=file_id,
            thumbnail_size=thumbnail_size,
        )

        mock_image_open.assert_called_once_with(mock_image_file)
        mock_image.thumbnail.assert_called_once_with(thumbnail_size, Image.Resampling.LANCZOS)  # type: ignore[attr-defined]
        assert expected_path.exists()

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

        mock_thumbnail_generator.synchronize_with_storage(
            storage_directory=mock_tmp_storage_path,
            files_metadata=files_metadata,
            thumbnail_size=thumbnail_size,
        )

        for metadata in files_metadata:
            assert mock_thumbnail_generator.get_thumbnail_path(file_id=metadata.id).exists()
