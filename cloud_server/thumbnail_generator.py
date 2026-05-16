"""Thumbnail generation for images and videos."""

import logging
from pathlib import Path

import cv2
from PIL import Image

from cloud_server.models import FileMetadata

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """Generate thumbnails for images and videos."""

    def __init__(self, thumbnails_directory: Path) -> None:
        """Initialize thumbnail generator.

        :param Path thumbnails_directory: Directory to save generated thumbnails
        """
        self._thumbnails_directory = thumbnails_directory
        self._thumbnails_directory.mkdir(parents=True, exist_ok=True)
        logger.info("Saving thumbnails to directory: %s", thumbnails_directory)

    def _generate_image_thumbnail(self, filepath: Path) -> Image.Image:
        """Generate thumbnail for an image file.

        :param Path filepath: Path to source image
        :return Image.Image: The generated thumbnail image
        """
        with Image.open(filepath) as img:
            thumbnail_img = img.copy()
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                thumbnail_img = background
            elif img.mode != "RGB":
                thumbnail_img = img.convert("RGB")

            return thumbnail_img

    def _generate_video_thumbnail(self, filepath: Path) -> Image.Image:
        """Generate thumbnail for a video file by extracting a frame.

        :param Path filepath: Path to source video
        :return Image.Image: The generated thumbnail image
        :raises OSError: If the video cannot be opened or read
        """
        if not (video := cv2.VideoCapture(filepath)).isOpened():
            error_msg = f"Could not open video file: {filepath}"
            logger.error(error_msg)
            raise OSError(error_msg)

        if (fps := video.get(cv2.CAP_PROP_FPS)) > 0:
            video.set(cv2.CAP_PROP_POS_FRAMES, int(fps))

        success, frame = video.read()
        video.release()

        if not success or frame is None:
            error_msg = f"Could not read frame from video: {filepath}"
            logger.error(error_msg)
            raise OSError(error_msg)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)

    def _save_thumbnail(self, img: Image.Image, output_path: Path, thumbnail_size: tuple[int, int]) -> None:
        """Save a PIL Image as a thumbnail.

        :param Image img: PIL Image to save
        :param Path output_path: Path to save the thumbnail
        :param tuple[int, int] thumbnail_size: Target thumbnail size (width, height)
        """
        img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", quality=85, optimize=True)

    def get_thumbnail_path(self, file_id: int) -> Path:
        """Get the thumbnail path for a given file ID.

        :param int file_id: Unique identifier for the file
        :return Path: Path to the thumbnail image
        """
        return self._thumbnails_directory / f"{file_id}.jpg"

    def generate_thumbnail(self, filepath: Path, mime_type: str, file_id: int, thumbnail_size: tuple[int, int]) -> None:
        """Generate thumbnail based on MIME type.

        :param Path filepath: Path to source file
        :param str mime_type: MIME type of the file
        :param int file_id: Unique identifier for the file
        :param tuple[int, int] thumbnail_size: Target thumbnail size (width, height)
        :raises FileExistsError: If a thumbnail already exists for the file
        :raises ValueError: If the MIME type is unsupported for thumbnail generation
        """
        if (output_path := self.get_thumbnail_path(file_id)).exists():
            error_msg = f"Thumbnail already exists for file {file_id}: {filepath}"
            logger.error(error_msg)
            raise FileExistsError(error_msg)

        if mime_type.startswith("image/"):
            thumbnail_img = self._generate_image_thumbnail(filepath=filepath)
        elif mime_type.startswith("video/"):
            thumbnail_img = self._generate_video_thumbnail(filepath=filepath)
        else:
            error_msg = f"Unsupported MIME type for thumbnail generation: {mime_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        self._save_thumbnail(img=thumbnail_img, output_path=output_path, thumbnail_size=thumbnail_size)

    def synchronize_with_storage(
        self, storage_directory: Path, files_metadata: list[FileMetadata], thumbnail_size: tuple[int, int]
    ) -> None:
        """Synchronize thumbnails with the storage directory by generating missing thumbnails and removing stale ones.

        :param Path storage_directory: Path to the server storage directory
        :param list[FileMetadata] files_metadata: File metadata in the database
        :param tuple[int, int] thumbnail_size: Target thumbnail size (width, height)
        """
        if not any(storage_directory.iterdir()):
            logger.warning("Storage directory is empty, skipping synchronization: %s", storage_directory)
            return

        existing_thumbnails = {int(thumbnail.stem) for thumbnail in self._thumbnails_directory.glob("*.jpg")}

        for file_metadata in files_metadata:
            if not file_metadata.mime_type.startswith(("image/", "video/")) or file_metadata.id is None:
                continue

            if file_metadata.id not in existing_thumbnails:
                if not (filepath := storage_directory / file_metadata.filepath).is_file():
                    error_msg = f"File {file_metadata.id} does not exist in storage: {filepath}"
                    logger.error(error_msg)
                    continue

                try:
                    self.generate_thumbnail(
                        filepath=filepath,
                        mime_type=file_metadata.mime_type,
                        file_id=file_metadata.id,
                        thumbnail_size=thumbnail_size,
                    )
                    logger.info("Generated thumbnail for file %d: %s", file_metadata.id, filepath)
                except Exception:
                    logger.exception("Failed to generate thumbnail for file %d: %s", file_metadata.id, filepath)
                    continue

            existing_thumbnails.discard(file_metadata.id)

        for stale_id in existing_thumbnails:
            stale_thumbnail = self.get_thumbnail_path(file_id=stale_id)

            try:
                stale_thumbnail.unlink()
                logger.info("Removed stale thumbnail for file %d: %s", stale_id, stale_thumbnail)
            except Exception:
                logger.exception("Failed to remove stale thumbnail for file %d: %s", stale_id, stale_thumbnail)
                continue

        logger.info(
            "Synchronized %d thumbnails with storage directory.", len(list(self._thumbnails_directory.glob("*.jpg")))
        )
