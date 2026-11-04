"""Unit tests for the cloud_server.routers.files_router module."""

import asyncio
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
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


class TestDownloadFolderEndpoint:
    """Integration tests for the GET /files/folders/download endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    @pytest.fixture
    def nested_folder(self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path) -> str:
        """Create folder/sub with files and register them in the DB."""
        for parent, name in (("dl", "a.txt"), ("dl/sub", "b.txt")):
            (mock_tmp_storage_path / parent).mkdir(parents=True, exist_ok=True)
            (mock_tmp_storage_path / parent / name).write_text(name)
            mock_files_router._db.perform_file_metadata_action(
                DatabaseAction.CREATE,
                file_metadata=FileMetadata(
                    filename=name, parent_directory=Path(parent), mime_type="text/plain", size=5
                ),
            )
        return "dl"

    def test_download_folder(
        self, mock_files_router: FilesRouter, mock_request_object: Request, nested_folder: str
    ) -> None:
        """A folder zip contains its files with paths relative to the folder."""
        response = asyncio.run(mock_files_router.download_folder(mock_request_object, path=nested_folder))
        with zipfile.ZipFile(response.path) as archive:
            assert sorted(archive.namelist()) == ["a.txt", "sub/b.txt"]
        Path(response.path).unlink()

    def test_download_root(
        self, mock_files_router: FilesRouter, mock_request_object: Request, nested_folder: str
    ) -> None:
        """Downloading '.' includes every tracked file."""
        response = asyncio.run(mock_files_router.download_folder(mock_request_object, path="."))
        with zipfile.ZipFile(response.path) as archive:
            assert {"dl/a.txt", "dl/sub/b.txt"} <= set(archive.namelist())
        Path(response.path).unlink()

    def test_download_missing_folder(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """A missing folder returns 404."""
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mock_files_router.download_folder(mock_request_object, path="nope"))
        assert exc.value.status_code == ResponseCode.NOT_FOUND

    def test_download_traversal(self, mock_files_router: FilesRouter, mock_request_object: Request) -> None:
        """Traversal outside storage is rejected."""
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mock_files_router.download_folder(mock_request_object, path="../.."))
        assert exc.value.status_code == ResponseCode.BAD_REQUEST


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


BOUNDARY = "----testboundary"


def make_upload_request(
    content: bytes,
    filename: str | None = "upload.txt",
    content_type: str = "text/plain",
    chunk_size: int = 7,
    *,
    extra_parts: bool = False,
) -> Request:
    """Build a real multipart Request whose body is delivered in small chunks, like a network stream."""
    parts = b""
    if extra_parts:
        parts += f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="other"\r\n\r\nignored\r\n'.encode()
    if filename is not None:
        parts += (
            (
                f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
            + content
            + b"\r\n"
        )
    body = parts + f"--{BOUNDARY}--\r\n".encode()
    chunks = [body[i : i + chunk_size] for i in range(0, len(body), chunk_size)]

    async def receive() -> dict:
        if chunks:
            return {"type": "http.request", "body": chunks.pop(0), "more_body": bool(chunks)}
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", f"multipart/form-data; boundary={BOUNDARY}".encode())],
    }
    return Request(scope, receive)


class TestUploadFileEndpoint:
    """Integration tests for the /files endpoint."""

    def test_upload_file(self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path) -> None:
        """Test a streamed upload is saved with the right contents and metadata."""
        content = bytes(range(256)) * 40  # Spans many chunks, includes bytes that look like boundaries/newlines
        request = make_upload_request(content, filename="data.bin", content_type="application/octet-stream")

        response = asyncio.run(mock_files_router.upload_file(request, "uploads"))

        assert response.message == "File uploaded successfully."
        assert response.file_metadata.filepath == Path("uploads/data.bin")
        assert response.file_metadata.mime_type == "application/octet-stream"
        assert response.file_metadata.size == len(content)
        assert (mock_tmp_storage_path / "uploads" / "data.bin").read_bytes() == content

    def test_upload_ignores_other_parts_and_empty_files(
        self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path
    ) -> None:
        """Test extra form fields are ignored and zero-byte files are stored."""
        request = make_upload_request(b"", filename="empty.txt", extra_parts=True)

        response = asyncio.run(mock_files_router.upload_file(request, "."))

        assert response.file_metadata.size == 0
        assert (mock_tmp_storage_path / "empty.txt").read_bytes() == b""

    def test_upload_image_generates_thumbnail(
        self,
        mock_files_router: FilesRouter,
        mock_image_open: MagicMock,
        mock_image_fromarray: MagicMock,
    ) -> None:
        """Test image uploads get a thumbnail generated before the response is returned."""
        request = make_upload_request(b"not-really-an-image", filename="pic.png", content_type="image/png")

        with patch.object(mock_files_router._thumbnail_generator, "generate_thumbnail") as mock_generate:
            response = asyncio.run(mock_files_router.upload_file(request, "."))

        mock_generate.assert_called_once()
        assert mock_generate.call_args.kwargs["file_id"] == response.file_metadata.id

    def test_upload_strips_path_from_filename(
        self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path
    ) -> None:
        """Test relative paths in the filename (sent by some browsers for folder uploads) are dropped."""
        request = make_upload_request(b"hi", filename="folder/sub/hi.txt")

        response = asyncio.run(mock_files_router.upload_file(request, "folder/sub"))

        assert response.file_metadata.filename == "hi.txt"
        assert (mock_tmp_storage_path / "folder" / "sub" / "hi.txt").read_bytes() == b"hi"

    def test_upload_existing_file_conflicts_without_leaving_temp_files(
        self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path
    ) -> None:
        """Test uploading an existing file returns 409, keeps the original and cleans up."""
        (mock_tmp_storage_path / "dup.txt").write_text("original")
        before = {p.name for p in mock_tmp_storage_path.iterdir()}

        with pytest.raises(HTTPException) as exc:
            asyncio.run(mock_files_router.upload_file(make_upload_request(b"new" * 100, filename="dup.txt"), "."))

        assert exc.value.status_code == ResponseCode.CONFLICT
        assert (mock_tmp_storage_path / "dup.txt").read_text() == "original"
        assert {p.name for p in mock_tmp_storage_path.iterdir()} == before

    def test_upload_existing_empty_file_conflicts(
        self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path
    ) -> None:
        """Test the conflict is also detected for zero-byte uploads, where no data chunk triggers the early check."""
        (mock_tmp_storage_path / "dup.txt").write_text("original")

        with pytest.raises(HTTPException) as exc:
            asyncio.run(mock_files_router.upload_file(make_upload_request(b"", filename="dup.txt"), "."))

        assert exc.value.status_code == ResponseCode.CONFLICT

    def test_upload_too_large(self, mock_files_router: FilesRouter, mock_tmp_storage_path: Path) -> None:
        """Test files over the size limit are rejected and not stored."""
        mock_files_router._storage_config.max_file_size_mb = 0
        before = {p.name for p in mock_tmp_storage_path.iterdir()}

        with pytest.raises(HTTPException) as exc:
            asyncio.run(mock_files_router.upload_file(make_upload_request(b"x" * 50), "."))

        assert exc.value.status_code == ResponseCode.BAD_REQUEST
        assert {p.name for p in mock_tmp_storage_path.iterdir()} == before

    @pytest.mark.parametrize("parent", ["../outside", "/etc"])
    def test_upload_rejects_invalid_parent_directory(self, mock_files_router: FilesRouter, parent: str) -> None:
        """Test traversal and absolute parent directories are rejected."""
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mock_files_router.upload_file(make_upload_request(b"x"), parent))

        assert exc.value.status_code == ResponseCode.BAD_REQUEST

    def test_upload_without_file_part(self, mock_files_router: FilesRouter) -> None:
        """Test a body with no file part is rejected."""
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mock_files_router.upload_file(make_upload_request(b"", filename=None), "."))

        assert exc.value.status_code == ResponseCode.BAD_REQUEST

    def test_upload_requires_multipart(self, mock_files_router: FilesRouter) -> None:
        """Test non-multipart requests are rejected."""
        request = Request({"type": "http", "method": "POST", "headers": [(b"content-type", b"text/plain")]})

        with pytest.raises(HTTPException) as exc:
            asyncio.run(mock_files_router.upload_file(request, "."))

        assert exc.value.status_code == ResponseCode.BAD_REQUEST


class TestUploadFileOverHttp:
    """Test the upload route through FastAPI, as a browser would call it."""

    @pytest.fixture
    def client(self, mock_files_router: FilesRouter) -> TestClient:
        """Provide a client for an app serving the real upload handler (the test limiter is a mock)."""
        app = FastAPI()
        app.add_api_route("/files/", mock_files_router.upload_file, methods=["POST"])
        return TestClient(app)

    def test_multipart_upload(self, client: TestClient, mock_tmp_storage_path: Path) -> None:
        """Test a normal multipart form upload is stored and returned."""
        content = b"abc" * 100_000

        response = client.post(
            "/files/", params={"parent_directory": "dir/sub"}, files={"file": ("big.txt", content, "text/plain")}
        )

        assert response.status_code == ResponseCode.OK
        assert response.json()["fileMetadata"]["size"] == len(content)
        assert (mock_tmp_storage_path / "dir" / "sub" / "big.txt").read_bytes() == content

    def test_duplicate_upload_returns_conflict(self, client: TestClient) -> None:
        """Test re-uploading the same file returns 409 over HTTP."""
        upload = {"file": ("same.txt", b"data" * 1000, "text/plain")}
        assert client.post("/files/", params={"parent_directory": "."}, files=upload).status_code == ResponseCode.OK

        response = client.post("/files/", params={"parent_directory": "."}, files=upload)

        assert response.status_code == ResponseCode.CONFLICT


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
