"""Unit tests for the cloud_server.routers.files_router module."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request, UploadFile
from fastapi.routing import APIRoute
from python_template_server.models import ResponseCode

from cloud_server.models import DatabaseAction, FileMetadata, MoveFolderRequest, UpdateFileMetadataRequest
from cloud_server.routers import FilesRouter


class TestRoutes:
    """Unit tests for route setup in FilesRouter."""

    def test_setup_routes(self, mock_files_router: FilesRouter) -> None:
        """Test that routes are set up correctly."""
        api_routes = [route for route in mock_files_router.router.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        expected_endpoints = [
            "/files/",
            "/files/folders/",
            "/files/{file_id}",
            "/files/{file_id}/metadata",
            "/files/{file_id}/thumbnail",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in routes


class TestMoveFolderEndpoint:
    """Integration tests for the PATCH /files/folders/ endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    @pytest.fixture
    def folder_with_files(self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path) -> str:
        """Create a folder with a file and register it in the DB."""
        folder_name = "test_folder"
        folder_dir = mock_tmp_storage_path / folder_name
        folder_dir.mkdir(parents=True, exist_ok=True)
        file_path = folder_dir / "sample.txt"
        file_path.write_text("hello")
        mock_files_router._db.perform_file_metadata_action(
            DatabaseAction.CREATE,
            file_metadata=FileMetadata(
                filename="sample.txt", parent_directory=Path(folder_name), mime_type="text/plain", size=5
            ),
        )
        return folder_name

    def test_move_folder(
        self,
        mock_files_router: FilesRouter,
        mock_request_object: Request,
        mock_tmp_storage_path: Path,
        folder_with_files: str,
    ) -> None:
        """Test renaming a folder and updating its file records."""
        old_name = folder_with_files
        new_name = "renamed_folder"
        body = MoveFolderRequest(newPath=new_name)

        response = asyncio.run(mock_files_router.move_folder(mock_request_object, path=old_name, body=body))

        assert "renamed_folder" in response.message
        assert response.files_updated >= 1
        assert (mock_tmp_storage_path / new_name).exists()
        assert not (mock_tmp_storage_path / old_name).exists()
        files = mock_files_router._db.list_files()
        assert any(str(f.parent_directory) == new_name for f in files)

    def test_move_folder_not_found(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test that moving a non-existent folder raises NOT_FOUND."""
        body = MoveFolderRequest(newPath="new_name")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_files_router.move_folder(mock_request_object, path="nonexistent", body=body))
        assert exc_info.value.status_code == ResponseCode.NOT_FOUND

    def test_move_folder_invalid_path(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test that path traversal attempts are rejected."""
        body = MoveFolderRequest(newPath="safe_name")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_files_router.move_folder(mock_request_object, path="../evil", body=body))
        assert exc_info.value.status_code == ResponseCode.BAD_REQUEST

    def test_move_folder_root_rejected(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test that moving the root directory is rejected."""
        body = MoveFolderRequest(newPath="safe_name")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_files_router.move_folder(mock_request_object, path=".", body=body))
        assert exc_info.value.status_code == ResponseCode.BAD_REQUEST


class TestDeleteFolderEndpoint:
    """Integration tests for the DELETE /files/folders/ endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    @pytest.fixture
    def folder_with_files(self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path) -> str:
        """Create a folder with a file and register it in the DB."""
        folder_name = "to_delete"
        folder_dir = mock_tmp_storage_path / folder_name
        folder_dir.mkdir(parents=True, exist_ok=True)
        file_path = folder_dir / "file.txt"
        file_path.write_text("data")
        mock_files_router._db.perform_file_metadata_action(
            DatabaseAction.CREATE,
            file_metadata=FileMetadata(
                filename="file.txt", parent_directory=Path(folder_name), mime_type="text/plain", size=4
            ),
        )
        return folder_name

    def test_delete_folder(
        self,
        mock_files_router: FilesRouter,
        mock_request_object: Request,
        mock_tmp_storage_path: Path,
        folder_with_files: str,
    ) -> None:
        """Test deleting a folder removes it from disk and DB."""
        folder_name = folder_with_files
        before = len(mock_files_router._db.list_files())

        response = asyncio.run(mock_files_router.delete_folder(mock_request_object, path=folder_name))

        assert response.files_deleted >= 1
        assert not (mock_tmp_storage_path / folder_name).exists()
        after = len(mock_files_router._db.list_files())
        assert after == before - response.files_deleted

    def test_delete_folder_not_found(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test that deleting a non-existent folder raises NOT_FOUND."""
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_files_router.delete_folder(mock_request_object, path="ghost_folder"))
        assert exc_info.value.status_code == ResponseCode.NOT_FOUND

    def test_delete_folder_invalid_path(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test that path traversal in delete is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_files_router.delete_folder(mock_request_object, path="../etc"))
        assert exc_info.value.status_code == ResponseCode.BAD_REQUEST


class TestListFilesEndpoint:
    """Integration tests for the /files endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_list_files(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test the /files endpoint method."""
        response = asyncio.run(mock_files_router.list_files(mock_request_object))

        assert response.message == "Files metadata retrieved successfully."
        assert len(response.files_metadata) > 0


class TestUploadFileEndpoint:
    """Integration tests for the /files endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_upload_file(  # noqa: PLR0917
        self,
        mock_files_router: FilesRouter,
        mock_request_object: Request,
        mock_tmp_storage_path: Path,
        mock_image_open: MagicMock,
        mock_video_capture: MagicMock,
        mock_cv2_cvtcolor: MagicMock,
        mock_image_fromarray: MagicMock,
    ) -> None:
        """Test the /files endpoint method."""
        files_metadata = [
            file_metadata
            for file_metadata in mock_files_router._db.list_files()
            if file_metadata.mime_type.startswith(("image/", "video/"))
        ]
        assert len(files_metadata) > 0

        for file_metadata in files_metadata:
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = f"new_{file_metadata.filename}"
            mock_file.content_type = file_metadata.mime_type

            file_contents = (mock_tmp_storage_path / file_metadata.filepath).read_bytes()
            chunk_size = mock_files_router._storage_config.upload_chunk_size_kb * 1024
            chunks_list = [file_contents[i : i + chunk_size] for i in range(0, len(file_contents), chunk_size)]
            chunks_list.append(b"")  # Empty chunk to signal end of file

            async def mock_read(size: int = -1, _chunks: list[bytes] = chunks_list) -> bytes:
                """Mock async read that returns chunks."""
                return _chunks.pop(0) if _chunks else b""

            mock_file.read = mock_read

            response = asyncio.run(
                mock_files_router.upload_file(mock_request_object, mock_file, str(file_metadata.parent_directory))
            )

            assert response.message == "File uploaded successfully."
            assert response.file_metadata.filepath == file_metadata.parent_directory / mock_file.filename
            assert response.file_metadata.mime_type == mock_file.content_type
            assert response.file_metadata.size == len(file_contents)


class TestGetFileEndpoint:
    """Integration tests for the /files/{file_id} endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_get_file(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test the /files/{file_id} endpoint method."""
        files_metadata = [
            file_metadata
            for file_metadata in mock_files_router._db.list_files()
            if file_metadata.mime_type.startswith(("image/", "video/"))
        ]
        assert len(files_metadata) > 0

        for file_metadata in files_metadata:
            file_id = file_metadata.id
            assert file_id is not None

            response = asyncio.run(mock_files_router.get_file(mock_request_object, file_id))

            assert response.path == (mock_files_router._storage_directory / file_metadata.filepath).resolve()
            assert response.filename == file_metadata.filename
            assert response.media_type == file_metadata.mime_type


class TestDeleteFileEndpoint:
    """Integration tests for the /files/{file_id} endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_delete_file(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test the /files/{file_id} endpoint method."""
        files_metadata = [
            file_metadata
            for file_metadata in mock_files_router._db.list_files()
            if file_metadata.mime_type.startswith(("image/", "video/"))
        ]
        assert len(files_metadata) > 0

        for file_metadata in files_metadata:
            file_id = file_metadata.id
            assert file_id is not None

            initial_files_count = len(mock_files_router._db.list_files())

            response = asyncio.run(mock_files_router.delete_file(mock_request_object, file_id))

            assert response.message == "File deleted successfully."
            assert response.file_metadata.filepath == file_metadata.filepath
            assert len(mock_files_router._db.list_files()) == initial_files_count - 1

            assert not (mock_files_router._storage_directory / file_metadata.filepath).exists()
            assert not mock_files_router._thumbnail_generator.get_thumbnail_path(file_id=file_id).exists()


class TestUpdateFileMetadataEndpoint:
    """Integration tests for the /files/{file_id}/metadata endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_update_file_metadata(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test the /files/{file_id}/metadata endpoint method."""
        files_metadata = [
            file_metadata
            for file_metadata in mock_files_router._db.list_files()
            if file_metadata.mime_type.startswith(("image/", "video/"))
        ]
        assert len(files_metadata) > 0

        for file_metadata in files_metadata:
            file_id = file_metadata.id
            assert file_id is not None

            update_request = UpdateFileMetadataRequest(
                filename=f"updated_{file_metadata.filename}",
                parent_directory=file_metadata.parent_directory / "updated_directory",
            )

            response = asyncio.run(mock_files_router.update_file_metadata(mock_request_object, file_id, update_request))

            assert response.message == "File metadata updated successfully."
            assert response.file_metadata.filepath == update_request.parent_directory / update_request.filename
            assert (mock_files_router._storage_directory / response.file_metadata.filepath).exists()
            assert not (mock_files_router._storage_directory / file_metadata.filepath).exists()


class TestGetThumbnailEndpoint:
    """Integration tests for the /files/{file_id}/thumbnail endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_get_thumbnail(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Test the /files/{file_id}/thumbnail endpoint method."""
        files_metadata = [
            file_metadata
            for file_metadata in mock_files_router._db.list_files()
            if file_metadata.mime_type.startswith(("image/", "video/"))
        ]
        assert len(files_metadata) > 0

        for file_metadata in files_metadata:
            file_id = file_metadata.id
            assert file_id is not None

            response = asyncio.run(mock_files_router.get_thumbnail(mock_request_object, file_id))

            assert response.path == mock_files_router._thumbnail_generator.get_thumbnail_path(file_id=file_id)
            assert response.filename == f"{file_id}.jpg"
            assert response.media_type == "image/jpeg"
