"""Unit tests for the cloud_server.routers.files_router module."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import Request, UploadFile
from fastapi.routing import APIRoute

from cloud_server.models import UpdateFileMetadataRequest
from cloud_server.routers import FilesRouter


class TestRoutes:
    """Unit tests for route setup in FilesRouter."""

    def test_setup_routes(self, mock_files_router: FilesRouter) -> None:
        """Test that routes are set up correctly."""
        api_routes = [route for route in mock_files_router.router.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        expected_endpoints = [
            "/files/",
            "/files/{file_id}",
            "/files/{file_id}/metadata",
            "/files/{file_id}/thumbnail",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in routes


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

    def test_upload_file(
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
                parent_directory=file_metadata.parent_directory / "updated_directory",  # type: ignore[call-arg]
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
