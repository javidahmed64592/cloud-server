"""Cloud server router with file operations endpoints."""

import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile

import aiofiles
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import MultipartParser, parse_options_header
from python_template_server.constants import MB_TO_BYTES
from python_template_server.models import ResponseCode
from python_template_server.routers import BaseRouter
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from cloud_server.db import FilesMetadataDatabaseManager
from cloud_server.models import (
    DatabaseAction,
    DeleteFileResponse,
    DeleteFolderResponse,
    FileMetadata,
    ListFilesResponse,
    MoveFolderRequest,
    MoveFolderResponse,
    StorageConfig,
    UpdateFileMetadataRequest,
    UpdateFileMetadataResponse,
    UploadFileResponse,
)
from cloud_server.thumbnail_generator import ThumbnailGenerator

logger = logging.getLogger(__name__)


@dataclass
class _ReceivedUpload:
    """A file received from a streamed multipart upload."""

    filename: str | None = None
    content_type: str = "application/octet-stream"
    size: int = 0
    temp_filepath: Path = field(default_factory=Path)
    failure: HTTPException | None = None

    @property
    def safe_filename(self) -> str:
        """Final path component of the received filename (browsers may send relative paths)."""
        return Path((self.filename or "").replace("\\", "/")).name

    def open_temp_file(self, directory: Path) -> Path:
        """Create the temporary file the upload is written to, returning its path."""
        with NamedTemporaryFile(delete=False, dir=directory) as temp_file:
            self.temp_filepath = Path(temp_file.name)
        return self.temp_filepath

    def discard(self) -> None:
        """Delete the temporary file if it exists."""
        self.temp_filepath.unlink(missing_ok=True)


class _FilePartCollector:
    """Collects the data of the multipart ``file`` part as the streaming parser emits it."""

    def __init__(self, received: _ReceivedUpload) -> None:
        """Initialize the collector.

        :param _ReceivedUpload received: Upload to fill in with the part's filename and content type
        """
        self._received = received
        self._pending: list[bytes] = []
        self._header_name = b""
        self._header_value = b""
        self._part_headers: dict[bytes, bytes] = {}
        self._collecting = False
        self.callbacks = {
            "on_part_begin": self._on_part_begin,
            "on_header_field": self._on_header_field,
            "on_header_value": self._on_header_value,
            "on_header_end": self._on_header_end,
            "on_headers_finished": self._on_headers_finished,
            "on_part_data": self._on_part_data,
            "on_part_end": self._on_part_end,
        }

    def take(self) -> bytes:
        """Return and clear the file data collected since the last call."""
        data = b"".join(self._pending)
        self._pending.clear()
        return data

    def _on_part_begin(self) -> None:
        self._header_name = self._header_value = b""
        self._part_headers = {}

    def _on_header_field(self, data: bytes, start: int, end: int) -> None:
        self._header_name += data[start:end]

    def _on_header_value(self, data: bytes, start: int, end: int) -> None:
        self._header_value += data[start:end]

    def _on_header_end(self) -> None:
        self._part_headers[self._header_name.lower()] = self._header_value
        self._header_name = self._header_value = b""

    def _on_headers_finished(self) -> None:
        _, disposition = parse_options_header(self._part_headers.get(b"content-disposition", b""))
        # Only the first "file" part is stored; any other parts are ignored
        if disposition.get(b"name") == b"file" and self._received.filename is None:
            self._received.filename = disposition.get(b"filename", b"").decode("utf-8", errors="replace")
            self._received.content_type = (
                self._part_headers.get(b"content-type", b"").decode() or "application/octet-stream"
            )
            self._collecting = True

    def _on_part_data(self, data: bytes, start: int, end: int) -> None:
        if self._collecting:
            self._pending.append(data[start:end])

    def _on_part_end(self) -> None:
        self._collecting = False


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

    def _cleanup_temp_file(self, temp_filepath: Path | None) -> None:
        """Clean up temporary file if it exists.

        :param Path | None temp_filepath: Path to temporary file or None
        """
        if temp_filepath and temp_filepath.exists():
            temp_filepath.unlink()

    def _resolve_folder_path(self, path: str, *, allow_root: bool = False) -> Path:
        """Validate and resolve a relative folder path, guarding against traversal."""
        folder = Path(path)
        if folder.is_absolute():
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="Folder path must be relative.")
        if str(folder) in (".", "") and not allow_root:
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="Cannot operate on the root directory.")
        storage = self._storage_directory.resolve()
        resolved = (self._storage_directory / folder).resolve()
        try:
            resolved.relative_to(storage)
        except ValueError as e:
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="Invalid folder path.") from e
        return folder

    def setup_routes(self) -> None:
        """Set up the API routes."""
        self.add_route(
            endpoint="/folders/",
            handler_function=self.move_folder,
            response_model=MoveFolderResponse,
            methods=["PATCH"],
            limited=True,
        )
        self.add_route(
            endpoint="/folders/download",
            handler_function=self.download_folder,
            response_model=None,
            methods=["GET"],
            limited=True,
        )
        self.add_route(
            endpoint="/folders/",
            handler_function=self.delete_folder,
            response_model=DeleteFolderResponse,
            methods=["DELETE"],
            limited=True,
        )

        self.add_route(
            endpoint="/",
            handler_function=self.list_files,
            response_model=ListFilesResponse,
            methods=["GET"],
            limited=True,
        )
        self.add_route(
            endpoint="/",
            handler_function=self.upload_file,
            response_model=UploadFileResponse,
            methods=["POST"],
            limited=True,
        )
        self.add_route(
            endpoint="/{file_id}",
            handler_function=self.get_file,
            response_model=None,
            methods=["GET"],
            limited=True,
        )
        self.add_route(
            endpoint="/{file_id}",
            handler_function=self.delete_file,
            response_model=DeleteFileResponse,
            methods=["DELETE"],
            limited=True,
        )
        self.add_route(
            endpoint="/{file_id}/metadata",
            handler_function=self.update_file_metadata,
            response_model=UpdateFileMetadataResponse,
            methods=["PATCH"],
            limited=True,
        )
        self.add_route(
            endpoint="/{file_id}/thumbnail",
            handler_function=self.get_thumbnail,
            response_model=None,
            methods=["GET"],
            limited=True,
        )

    async def move_folder(self, request: Request, path: str, body: MoveFolderRequest) -> MoveFolderResponse:
        """Rename or move a folder and update all contained file records.

        :param Request request: The incoming HTTP request
        :param str path: Current folder path relative to storage directory (query param)
        :param MoveFolderRequest body: Request body containing the new folder path
        :return MoveFolderResponse: Folder move response
        :raises HTTPException: If path validation fails or the folder doesn't exist
        """
        old_folder = self._resolve_folder_path(path)
        new_folder = self._resolve_folder_path(body.new_path)

        old_dir = self._storage_directory / old_folder
        new_dir = self._storage_directory / new_folder

        if not old_dir.exists():
            error_msg = f"Folder not found in storage: {path}"
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg)

        if new_dir.exists():
            error_msg = f"Folder already exists in storage: {body.new_path}"
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.CONFLICT, detail=error_msg)

        count = self._db.rename_folder(str(old_folder), str(new_folder))
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        old_dir.rename(new_dir)
        logger.info("Moved folder from '%s' to '%s' (%d files updated)", path, body.new_path, count)

        return MoveFolderResponse(
            message=f"Folder moved from '{path}' to '{body.new_path}' successfully.",
            files_updated=count,
        )

    def _build_folder_zip(self, folder: Path, zip_path: Path) -> int:
        """Zip all tracked files under ``folder`` (``.`` for everything), returning the file count."""
        prefix = str(folder)
        count = 0
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for file_metadata in self._db.list_files():
                parent = str(file_metadata.parent_directory)
                in_folder = prefix in {".", parent} or parent.startswith(f"{prefix}/")
                if not in_folder:
                    continue
                source = self._storage_directory / file_metadata.filepath
                if not source.is_file():
                    continue
                arcname = file_metadata.filepath if prefix == "." else file_metadata.filepath.relative_to(folder)
                archive.write(source, arcname=str(arcname))
                count += 1
        return count

    async def download_folder(self, request: Request, path: str = ".") -> FileResponse:
        """Download a folder (or the entire storage directory with ``path=.``) as a zip archive.

        :param Request request: The incoming HTTP request
        :param str path: Folder path relative to storage directory; ``.`` downloads everything
        :return FileResponse: The zip archive
        :raises HTTPException: If path validation fails or the folder has no files
        """
        folder = self._resolve_folder_path(path, allow_root=True)
        if str(folder) != "." and not (self._storage_directory / folder).is_dir():
            error_msg = f"Folder not found in storage: {path}"
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg)

        with NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            zip_path = Path(tmp.name)
        try:
            count = await run_in_threadpool(self._build_folder_zip, folder, zip_path)
        except Exception as e:
            self._cleanup_temp_file(temp_filepath=zip_path)
            error_msg = f"Failed to create archive for folder: {path}"
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.INTERNAL_SERVER_ERROR, detail=error_msg) from e

        if count == 0:
            self._cleanup_temp_file(temp_filepath=zip_path)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=f"No files to download in: {path}")

        name = "storage" if str(folder) == "." else folder.name
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"{name}.zip",
            background=BackgroundTask(self._cleanup_temp_file, temp_filepath=zip_path),
        )

    async def delete_folder(self, request: Request, path: str) -> DeleteFolderResponse:
        """Delete a folder and all its contents.

        :param Request request: The incoming HTTP request
        :param str path: Folder path relative to storage directory (query param)
        :return DeleteFolderResponse: Folder deletion response
        :raises HTTPException: If path validation fails or the folder doesn't exist
        """
        folder = self._resolve_folder_path(path)
        folder_dir = self._storage_directory / folder

        if not folder_dir.exists():
            error_msg = f"Folder not found in storage: {path}"
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=error_msg)

        deleted_files = self._db.delete_files_in_folder(str(folder))
        for file_metadata in deleted_files:
            thumbnail_path = self._thumbnail_generator.get_thumbnail_path(file_id=file_metadata.id)  # ty:ignore[invalid-argument-type]
            if thumbnail_path.exists():
                thumbnail_path.unlink()

        shutil.rmtree(folder_dir)
        logger.info("Deleted folder '%s' with %d files", path, len(deleted_files))

        return DeleteFolderResponse(
            message=f"Folder '{path}' deleted successfully.",
            files_deleted=len(deleted_files),
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

    async def _receive_upload(self, request: Request, parent_path: Path) -> _ReceivedUpload:
        """Stream the multipart request body straight to a temporary file in storage.

        The file is written to disk as its bytes arrive rather than being buffered and copied afterwards,
        so by the time the request body has been fully received the file has already been saved.

        :param Request request: The incoming HTTP request
        :param Path parent_path: Validated parent directory the file will be stored in
        :return _ReceivedUpload: Details of the received file and where it was written
        :raises HTTPException: If the body is malformed, the file already exists, or the file is too large
        """
        content_type, options = parse_options_header(request.headers.get("content-type", ""))
        if content_type != b"multipart/form-data" or b"boundary" not in options:
            error_msg = "Upload must be sent as multipart/form-data."
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg)

        max_size_bytes = self._storage_config.max_file_size_mb * MB_TO_BYTES
        received = _ReceivedUpload()
        collector = _FilePartCollector(received)
        conflict_checked = False

        try:
            parser = MultipartParser(options[b"boundary"], callbacks=collector.callbacks)
            async with aiofiles.open(received.open_temp_file(self._storage_directory), "wb") as f:
                async for chunk in request.stream():
                    parser.write(chunk)
                    if not (data := collector.take()):
                        continue
                    received.size += len(data)
                    if received.failure is None:
                        received.failure = self._check_incoming_file(
                            received, parent_path, max_size_bytes, check_exists=not conflict_checked
                        )
                        conflict_checked = True
                    # On failure the rest of the body is still drained (but not stored) so the client receives
                    # the error response instead of a connection reset while it is mid-upload.
                    if received.failure is None:
                        await f.write(data)
                parser.finalize()
        except MultipartParseError as e:
            received.discard()
            error_msg = "Malformed multipart upload."
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg) from e
        except Exception as e:
            received.discard()
            error_msg = "Failed to receive uploaded file."
            logger.exception(error_msg)
            raise HTTPException(status_code=ResponseCode.INTERNAL_SERVER_ERROR, detail=error_msg) from e

        if received.failure is not None:
            received.discard()
            raise received.failure
        if received.filename is None:
            received.discard()
            error_msg = "Filename is required for file upload."
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg)
        return received

    def _check_incoming_file(
        self, received: _ReceivedUpload, parent_path: Path, max_size_bytes: int, *, check_exists: bool
    ) -> HTTPException | None:
        """Check a file that is currently being received, returning the error to raise once it has been drained.

        :param _ReceivedUpload received: The upload being received
        :param Path parent_path: Parent directory the file will be stored in
        :param int max_size_bytes: Maximum allowed file size
        :param bool check_exists: Whether to check if the file already exists in storage
        :return HTTPException | None: The error to raise, or None if the file is acceptable so far
        """
        if received.size > max_size_bytes:
            error_msg = f"File size exceeds maximum allowed size ({max_size_bytes} bytes)"
            logger.error(error_msg)
            return HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg)

        if check_exists and (self._storage_directory / parent_path / received.safe_filename).exists():
            error_msg = f"File already exists in storage: {parent_path / received.safe_filename}"
            logger.error(error_msg)
            return HTTPException(status_code=ResponseCode.CONFLICT, detail=error_msg)

        return None

    async def upload_file(self, request: Request, parent_directory: str) -> UploadFileResponse:
        """Upload a file.

        The request body is streamed directly to storage as it arrives (see :meth:`_receive_upload`).

        :param Request request: The incoming HTTP request containing the multipart ``file`` part
        :param str parent_directory: Parent directory path relative to storage directory
        :return UploadFileResponse: File upload response
        :raises HTTPException: If file validation fails or storage operation fails
        """
        # Guard against absolute paths and traversal outside the storage directory
        parent_path = Path(parent_directory)
        resolved_parent = (self._storage_directory / parent_path).resolve()
        if parent_path.is_absolute() or not resolved_parent.is_relative_to(self._storage_directory.resolve()):
            error_msg = f"Invalid parent directory: {parent_directory}"
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg)

        received = await self._receive_upload(request, parent_path)
        temp_filepath = received.temp_filepath

        # Browsers may send a relative path (e.g. "folder/sub/file.txt") as the filename for folder uploads,
        # so only the final path component is kept.
        filename = received.safe_filename
        if not filename or filename in {".", ".."}:
            received.discard()
            error_msg = "Filename is required for file upload."
            logger.error(error_msg)
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=error_msg)

        # Create file metadata
        file_metadata = FileMetadata(
            id=None,
            filename=filename,
            parent_directory=parent_path,
            mime_type=received.content_type,
            size=received.size,
        )

        # Ensure parent directory exists
        full_parent_dir = self._storage_directory / file_metadata.parent_directory
        full_parent_dir.mkdir(parents=True, exist_ok=True)

        # Checked again as another upload may have created the file while this one was being received
        if (filepath := self._storage_directory / file_metadata.filepath).exists():
            error_msg = f"File already exists in storage: {filepath}"
            logger.error(error_msg)
            received.discard()
            raise HTTPException(status_code=ResponseCode.CONFLICT, detail=error_msg)

        # Move temp file to final location
        try:
            temp_filepath.rename(filepath)
        except OSError as e:
            error_msg = f"Failed to move file to final location: {filepath}"
            logger.exception(error_msg)
            received.discard()
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
            # Run in a worker thread: decoding images/videos would otherwise block every other request
            await run_in_threadpool(
                self._thumbnail_generator.generate_thumbnail,
                filepath=filepath,
                mime_type=file_metadata.mime_type,
                file_id=created_file_metadata.id,  # ty:ignore[invalid-argument-type]
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

        thumbnail_path = self._thumbnail_generator.get_thumbnail_path(file_id=file_metadata.id)  # ty:ignore[invalid-argument-type]

        return FileResponse(
            path=thumbnail_path,
            filename=thumbnail_path.name,
            media_type="image/jpeg",
        )
