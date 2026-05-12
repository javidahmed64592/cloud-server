"""Cloud server router with file operations endpoints."""

from pathlib import Path

from fastapi import Request
from python_template_server.routers import BaseRouter

from cloud_server.db import FilesMetadataDatabaseManager
from cloud_server.models import (
    AddFileMetadataResponse,
    DatabaseAction,
    DeleteFileMetadataResponse,
    GetFileMetadataResponse,
    GetFilesMetadataResponse,
    UpdateFileMetadataResponse,
)


class FilesRouter(BaseRouter):
    """Router for the cloud server file operations."""

    def configure_router(self, db: FilesMetadataDatabaseManager, storage_directory: Path) -> None:
        """Configure the router with necessary dependencies."""
        self._db = db
        self._storage_directory = storage_directory

    def setup_routes(self) -> None:
        """Set up the API routes."""
        self.add_route(
            endpoint="/",
            handler_function=self.get_files_metadata,
            response_model=GetFilesMetadataResponse,
            methods=["GET"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/",
            handler_function=self.add_file_metadata,
            response_model=AddFileMetadataResponse,
            methods=["POST"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/{file_id}",
            handler_function=self.update_file_metadata,
            response_model=UpdateFileMetadataResponse,
            methods=["PATCH"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/{file_id}",
            handler_function=self.delete_file_metadata,
            response_model=DeleteFileMetadataResponse,
            methods=["DELETE"],
            limited=True,
            authentication_required=True,
        )
        self.add_route(
            endpoint="/{file_id}",
            handler_function=self.get_file_metadata,
            response_model=GetFileMetadataResponse,
            methods=["GET"],
            limited=True,
            authentication_required=True,
        )

    async def get_files_metadata(self, request: Request) -> GetFilesMetadataResponse:
        """Get metadata for all files.

        :param Request request: The incoming HTTP request
        :return GetFilesMetadataResponse: Files metadata response
        """
        return GetFilesMetadataResponse(
            message="Files metadata retrieved successfully.",
            files_metadata=self._db.list_files(),
        )
