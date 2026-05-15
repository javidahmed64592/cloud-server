"""Unit tests for the cloud_server.routers.files_router module."""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import Request, UploadFile
from fastapi.routing import APIRoute

from cloud_server.models import FileMetadata, UpdateFileMetadataRequest
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
        self, mock_files_router: FilesRouter, mock_request_object: Request, mock_file_metadata: FileMetadata
    ) -> None:
        """Test the /files endpoint method."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = f"new_{mock_file_metadata.filename}"
        mock_file.content_type = mock_file_metadata.mime_type
        mock_file.read.return_value = b"Test file content"

        response = asyncio.run(
            mock_files_router.upload_file(mock_request_object, mock_file, mock_file_metadata.parent_directory)
        )

        assert response.message == "File uploaded successfully."
        assert response.file_metadata.filepath == mock_file_metadata.parent_directory / mock_file.filename
        assert response.file_metadata.mime_type == mock_file.content_type
        assert response.file_metadata.size == len(mock_file.read.return_value)


class TestGetFileEndpoint:
    """Integration tests for the /files/{file_id} endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_get_file(
        self, mock_files_router: FilesRouter, mock_request_object: Request, mock_file_metadata: FileMetadata
    ) -> None:
        """Test the /files/{file_id} endpoint method."""
        file_id = mock_files_router._db.list_files()[0].id

        response = asyncio.run(mock_files_router.get_file(mock_request_object, file_id))

        assert response.path == (mock_files_router._storage_directory / mock_file_metadata.filepath).resolve()
        assert response.filename == mock_file_metadata.filename
        assert response.media_type == mock_file_metadata.mime_type


class TestDeleteFileEndpoint:
    """Integration tests for the /files/{file_id} endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_delete_file(
        self, mock_files_router: FilesRouter, mock_request_object: Request, mock_file_metadata: FileMetadata
    ) -> None:
        """Test the /files/{file_id} endpoint method."""
        file_id = mock_files_router._db.list_files()[0].id

        response = asyncio.run(mock_files_router.delete_file(mock_request_object, file_id))

        assert response.message == "File deleted successfully."
        assert response.file_metadata.filepath == mock_file_metadata.filepath
        assert len(mock_files_router._db.list_files()) == 0


class TestUpdateFileMetadataEndpoint:
    """Integration tests for the /files/{file_id}/metadata endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_update_file_metadata(
        self, mock_files_router: FilesRouter, mock_request_object: Request, mock_file_metadata: FileMetadata
    ) -> None:
        """Test the /files/{file_id}/metadata endpoint method."""
        file_id = mock_files_router._db.list_files()[0].id
        update_request = UpdateFileMetadataRequest(
            filename=f"updated_{mock_file_metadata.filename}",
            parent_directory=mock_file_metadata.parent_directory / "updated_directory",
        )

        response = asyncio.run(mock_files_router.update_file_metadata(mock_request_object, file_id, update_request))

        assert response.message == "File metadata updated successfully."
        assert response.file_metadata.filepath == update_request.parent_directory / update_request.filename
        assert (mock_files_router._storage_directory / response.file_metadata.filepath).exists()
        assert not (mock_files_router._storage_directory / mock_file_metadata.filepath).exists()
