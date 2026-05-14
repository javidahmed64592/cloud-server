"""Cloud server router with file operations endpoints."""

import logging
from pathlib import Path

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
    GetFileMetadataResponse,
    ListFilesResponse,
    StorageConfig,
    UpdateFileMetadataRequest,
    UpdateFileMetadataResponse,
    UploadFileResponse,
)

logger = logging.getLogger(__name__)


class FilesRouter(BaseRouter):
    """Router for the cloud server file operations."""

    def configure_router(
        self, db: FilesMetadataDatabaseManager, storage_directory: Path, storage_config: StorageConfig
    ) -> None:
        """Configure the router with necessary dependencies."""
        self._db = db
        self._storage_directory = storage_directory
        self._storage_config = storage_config

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
            handler_function=self.get_file_metadata,
            response_model=GetFileMetadataResponse,
            methods=["GET"],
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

        # Validate file size
        max_size_bytes = self._storage_config.max_file_size_mb * MB_TO_BYTES
        file_size = 0

        # Read file to determine size
        file_contents = await file.read()
        file_size = len(file_contents)

        if file_size > max_size_bytes:
            error_msg = f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size_bytes} bytes)"
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg)

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
            raise HTTPException(status_code=ResponseCode.CONFLICT, detail=error_msg)

        # Save file to storage using chunked writing
        try:
            chunk_size = self._storage_config.upload_chunk_size_kb * 1024
            async with aiofiles.open(filepath, "wb") as f:
                for i in range(0, len(file_contents), chunk_size):
                    await f.write(file_contents[i : i + chunk_size])
        except OSError as e:
            error_msg = f"Failed to write file to storage: {filepath}"
            logger.exception(error_msg)
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
        return DeleteFileResponse(
            message="File deleted successfully.",
            file_metadata=file_metadata,
        )

    async def get_file_metadata(self, request: Request, file_id: int) -> GetFileMetadataResponse:
        """Get metadata for a file by its ID.

        :param Request request: The incoming HTTP request
        :param int file_id: The ID of the file to retrieve metadata for
        :return GetFileMetadataResponse: File metadata response
        :raises HTTPException: If the file metadata doesn't exist in the database
        """
        # Retrieve file metadata from database
        try:
            file_metadata = self._db.perform_file_metadata_action(action=DatabaseAction.READ, file_id=file_id)
        except ValueError as e:
            error_msg = f"File metadata doesn't exist in database for file {file_id}!"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg) from e

        return GetFileMetadataResponse(
            message="File metadata retrieved successfully.",
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

        return UpdateFileMetadataResponse(
            message="File metadata updated successfully.",
            file_metadata=updated_file_metadata,
        )
