"""Cloud server router with file operations endpoints."""

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

import aiofiles
from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from python_template_server.constants import MB_TO_BYTES
from python_template_server.models import ResponseCode
from python_template_server.routers import BaseRouter

from cloud_server.db import FilesMetadataDatabaseManager
from cloud_server.models import (
    DatabaseAction,
    DeleteFileResponse,
    FileMetadata,
    ListFilesResponse,
    StorageConfig,
    UpdateFileMetadataRequest,
    UpdateFileMetadataResponse,
    UploadFileResponse,
)
from cloud_server.thumbnail_generator import ThumbnailGenerator

logger = logging.getLogger(__name__)


class FilesRouter(BaseRouter):
    """Router for the cloud server file operations."""

    def configure_router(
        self,
        db: FilesMetadataDatabaseManager,
        storage_directory: Path,
        storage_config: StorageConfig,
        thumbnail_generator: ThumbnailGenerator,
    ) -> None:
        """Configure the router with necessary dependencies."""
        self._db = db
        self._storage_directory = storage_directory
        self._storage_config = storage_config
        self._thumbnail_generator = thumbnail_generator

    def _raise_file_size_exceeded(self, file_size: int, max_size: int) -> None:
        """Raise HTTPException for file size exceeded.

        :param int file_size: The actual file size
        :param int max_size: The maximum allowed size
        :raises HTTPException: Always raises with BAD_REQUEST status
        """
        error_msg = f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        logger.error(error_msg)
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg)

    async def _stream_upload_to_temp(
        self, file: UploadFile, temp_filepath: Path, max_size_bytes: int, chunk_size: int
    ) -> int:
        """Stream uploaded file to temporary location while validating size.

        :param UploadFile file: The file being uploaded
        :param Path temp_filepath: Path to temporary file
        :param int max_size_bytes: Maximum allowed file size
        :param int chunk_size: Size of chunks to read
        :return int: Total file size in bytes
        :raises HTTPException: If file size exceeds maximum
        """
        file_size = 0
        async with aiofiles.open(temp_filepath, "wb") as f:
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                if file_size > max_size_bytes:
                    self._raise_file_size_exceeded(file_size, max_size_bytes)
                await f.write(chunk)
        return file_size

    def _cleanup_temp_file(self, temp_filepath: Path | None) -> None:
        """Clean up temporary file if it exists.

        :param Path | None temp_filepath: Path to temporary file or None
        """
        if temp_filepath and temp_filepath.exists():
            temp_filepath.unlink()

    def setup_routes(self) -> None:
        """Set up the API routes."""
        self.add_route(
            endpoint="/",
            handler_function=self.list_files,
            response_model=ListFilesResponse,
            methods=["GET"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/",
            handler_function=self.upload_file,
            response_model=UploadFileResponse,
            methods=["POST"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/{file_id}",
            handler_function=self.get_file,
            response_model=None,
            methods=["GET"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/{file_id}",
            handler_function=self.delete_file,
            response_model=DeleteFileResponse,
            methods=["DELETE"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/{file_id}/metadata",
            handler_function=self.update_file_metadata,
            response_model=UpdateFileMetadataResponse,
            methods=["PATCH"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/{file_id}/thumbnail",
            handler_function=self.get_thumbnail,
            response_model=None,
            methods=["GET"],
            limited=True,
            authentication_required=True,
        )

    async def list_files(self, request: Request) -> ListFilesResponse:
        """Get metadata for all files.

        :param Request request: The incoming HTTP request
        :return ListFilesResponse: Files metadata response
        """
        files_metadata = self._db.list_files()
        if len(files_metadata) == 0:
            logger.warning("No files found in database.")

        return ListFilesResponse(
            message="Files metadata retrieved successfully.",
            files_metadata=files_metadata,
        )

    async def upload_file(self, request: Request, file: UploadFile, parent_directory: str) -> UploadFileResponse:
        """Upload a file.

        :param Request request: The incoming HTTP request
        :param UploadFile file: The file to upload
        :param str parent_directory: Parent directory path relative to storage directory
        :return UploadFileResponse: File upload response
        :raises HTTPException: If file validation fails or storage operation fails
        """
        # Validate filename
        if not file.filename:
            error_msg = "Filename is required for file upload."
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg)

        # Stream file to temp location while validating size
        max_size_bytes = self._storage_config.max_file_size_mb * MB_TO_BYTES
        chunk_size = self._storage_config.upload_chunk_size_kb * 1024
        temp_filepath = None

        try:
            temp_file = NamedTemporaryFile(delete=False, dir=self._storage_directory)
            temp_filepath = Path(temp_file.name)
            temp_file.close()

            file_size = await self._stream_upload_to_temp(
                file=file, temp_filepath=temp_filepath, max_size_bytes=max_size_bytes, chunk_size=chunk_size
            )

        except Exception as e:
            self._cleanup_temp_file(temp_filepath=temp_filepath)
            error_msg = f"Failed to read uploaded file: {file.filename}"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.INTERNAL_SERVER_ERROR, detail=error_msg) from e

        # Create file metadata
        file_metadata = FileMetadata(
            id=None,
            filename=file.filename,
            parent_directory=Path(parent_directory),
            mime_type=file.content_type or "application/octet-stream",
            size=file_size,
        )

        # Ensure parent directory exists
        full_parent_dir = self._storage_directory / file_metadata.parent_directory
        full_parent_dir.mkdir(parents=True, exist_ok=True)

        if (filepath := self._storage_directory / file_metadata.filepath).exists():
            error_msg = f"File already exists in storage: {filepath}"
            logger.error(error_msg)
            self._cleanup_temp_file(temp_filepath=temp_filepath)
            raise HTTPException(status_code=ResponseCode.CONFLICT, detail=error_msg)

        # Move temp file to final location
        try:
            temp_filepath.rename(filepath)
        except OSError as e:
            error_msg = f"Failed to move file to final location: {filepath}"
            logger.exception(error_msg)
            self._cleanup_temp_file(temp_filepath=temp_filepath)
            raise HTTPException(status_code=ResponseCode.INTERNAL_SERVER_ERROR, detail=error_msg) from e

        try:
            created_file_metadata = self._db.perform_file_metadata_action(
                action=DatabaseAction.CREATE, file_metadata=file_metadata
            )
        except ValueError as e:
            # Cleanup the file if database operation fails
            if filepath.exists():
                filepath.unlink()
            error_msg = f"Failed to create file metadata in database for file: {file_metadata}"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.INTERNAL_SERVER_ERROR, detail=error_msg) from e

        if file_metadata.mime_type.startswith(("image/", "video/")):
            self._thumbnail_generator.generate_thumbnail(
                filepath=filepath,
                mime_type=file_metadata.mime_type,
                file_id=created_file_metadata.id,  # type: ignore[arg-type]
                thumbnail_size=self._storage_config.thumbnail_size,
            )

        return UploadFileResponse(
            message="File uploaded successfully.",
            file_metadata=created_file_metadata,
        )

    async def get_file(self, request: Request, file_id: int) -> FileResponse:
        """Get a file by its ID.

        :param Request request: The incoming HTTP request
        :param int file_id: The ID of the file to retrieve
        :return FileResponse: The requested file
        :raises HTTPException: If the file metadata doesn't exist in the database or if the file is not found in storage
        """
        # Retrieve file metadata from database
        try:
            file_metadata = self._db.perform_file_metadata_action(action=DatabaseAction.READ, file_id=file_id)
        except ValueError as e:
            error_msg = f"File metadata doesn't exist in database for file {file_id}!"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg) from e

        # Validate file exists in storage
        if not (filepath := self._storage_directory / file_metadata.filepath).exists():
            error_msg = f"File {file_id} not found in storage: {filepath}"
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg)

        return FileResponse(
            path=filepath,
            filename=file_metadata.filename,
            media_type=file_metadata.mime_type,
        )

    async def delete_file(self, request: Request, file_id: int) -> DeleteFileResponse:
        """Delete a file by its ID.

        :param Request request: The incoming HTTP request
        :param int file_id: The ID of the file to delete
        :return DeleteFileResponse: File deletion response
        :raises HTTPException: If the file metadata doesn't exist in the database or if the file is not found in storage
        """
        # First, delete the file metadata from the database to get the file path, then delete the file from storage
        try:
            file_metadata = self._db.perform_file_metadata_action(action=DatabaseAction.DELETE, file_id=file_id)
        except ValueError as e:
            error_msg = f"File metadata doesn't exist in database for file {file_id}!"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg) from e

        # Validate file exists in storage before attempting to delete
        if not (filepath := self._storage_directory / file_metadata.filepath).exists():
            error_msg = f"File {file_id} not found in storage: {filepath}"
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg)

        filepath.unlink()
        logger.info("Deleted file %s from storage: %s", file_id, filepath)

        if not any(filepath.parent.iterdir()):
            filepath.parent.rmdir()
            logger.info("Deleted empty parent directory: %s", filepath.parent)

        if (thumbnail_path := self._thumbnail_generator.get_thumbnail_path(file_id=file_id)).exists():
            thumbnail_path.unlink()

        return DeleteFileResponse(
            message="File deleted successfully.",
            file_metadata=file_metadata,
        )

    async def update_file_metadata(
        self, request: Request, file_id: int, body: UpdateFileMetadataRequest
    ) -> UpdateFileMetadataResponse:
        """Update metadata for a file by its ID.

        :param Request request: The incoming HTTP request
        :param int file_id: The ID of the file to update metadata for
        :param UpdateFileMetadataRequest body: The updated filename and parent directory
        :return UpdateFileMetadataResponse: File metadata update response
        :raises HTTPException: If the file metadata doesn't exist in the database or file operations fail
        """
        # Retrieve existing metadata to get current filename and parent directory
        try:
            old_metadata = self._db.perform_file_metadata_action(action=DatabaseAction.READ, file_id=file_id)
        except ValueError as e:
            error_msg = f"File metadata doesn't exist in database for file {file_id}!"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg) from e

        # Construct new metadata with updated filename and parent directory
        new_metadata = FileMetadata(
            id=file_id,
            filename=body.filename or old_metadata.filename,
            parent_directory=body.parent_directory or old_metadata.parent_directory,
            mime_type=old_metadata.mime_type,
            size=old_metadata.size,
        )

        # Update metadata in database and get the updated metadata
        try:
            updated_file_metadata = self._db.perform_file_metadata_action(
                action=DatabaseAction.UPDATE, file_id=file_id, file_metadata=new_metadata
            )
        except ValueError as e:
            error_msg = f"File metadata doesn't exist in database for file {file_id}!"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg) from e

        # If filepath changed, rename/move the file in storage
        if old_metadata.filepath != updated_file_metadata.filepath:
            old_filepath = self._storage_directory / old_metadata.filepath
            new_filepath = self._storage_directory / updated_file_metadata.filepath

            if not old_filepath.exists():
                error_msg = f"File {file_id} not found in storage: {old_filepath}"
                logger.error(error_msg)
                raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg)

            if new_filepath.exists():
                error_msg = f"File {file_id} already exists in storage: {new_filepath}"
                logger.error(error_msg)
                raise HTTPException(status_code=ResponseCode.CONFLICT, detail=error_msg)

            new_filepath.parent.mkdir(parents=True, exist_ok=True)
            old_filepath.rename(new_filepath)
            logger.info("Moved file %s in storage from %s to %s", file_id, old_filepath, new_filepath)

            if not any(old_filepath.parent.iterdir()):
                old_filepath.parent.rmdir()
                logger.info("Deleted empty parent directory: %s", old_filepath.parent)

        return UpdateFileMetadataResponse(
            message="File metadata updated successfully.",
            file_metadata=updated_file_metadata,
        )

    async def get_thumbnail(self, request: Request, file_id: int) -> FileResponse:
        """Get a thumbnail for a file by its ID.

        :param Request request: The incoming HTTP request
        :param int file_id: The ID of the file to get a thumbnail for
        :return FileResponse: The requested thumbnail image
        :raises HTTPException: If the file metadata doesn't exist in the database or if the file is not found in storage
        """
        # Retrieve file metadata from database
        try:
            file_metadata = self._db.perform_file_metadata_action(action=DatabaseAction.READ, file_id=file_id)
        except ValueError as e:
            error_msg = f"File metadata doesn't exist in database for file {file_id}!"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg) from e

        thumbnail_path = self._thumbnail_generator.get_thumbnail_path(file_id=file_metadata.id)  # type: ignore[arg-type]

        return FileResponse(
            path=thumbnail_path,
            filename=thumbnail_path.name,
            media_type="image/jpeg",
        )
