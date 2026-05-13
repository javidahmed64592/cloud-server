"""Pydantic models for the server."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from python_template_server.models import BaseResponse, DatabaseConfig, TemplateServerConfig


# Cloud Server Configuration Models
class ServerDatabaseConfig(DatabaseConfig):
    """Configuration for the server database."""

    files_metadata_db_filename: str = Field(
        default="files_metadata.db", description="The filename for the files metadata database."
    )


class StorageConfig(BaseModel):
    """Configuration model for the cloud storage."""

    upload_chunk_size_kb: int = Field(default=8, description="Chunk size for file uploads in KB.")
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB.")


class CloudServerConfig(TemplateServerConfig):
    """Cloud server configuration."""

    db: ServerDatabaseConfig = Field(default_factory=ServerDatabaseConfig, description="Database configuration.")
    storage_config: StorageConfig = Field(default_factory=StorageConfig, description="Storage configuration.")


# Database
def current_timestamp_int() -> int:
    """Get the current Unix timestamp as an integer.

    :return int: The current Unix timestamp
    """
    return int(datetime.fromisoformat(BaseResponse.current_timestamp().rstrip("Z")).timestamp())


class DatabaseAction(StrEnum):
    """Enumeration for database actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


# File Models
class FileMetadata(BaseModel):
    """Model for file metadata stored in the index."""

    id: int | None = Field(default=None, description="Unique identifier for the file.")
    filename: str = Field(..., description="Original filename of the uploaded file.")
    parent_directory: Path = Field(..., description="Path to parent directory relative to server storage directory.")
    mime_type: str = Field(..., description="MIME type of the file.")
    size: int = Field(..., description="File size in bytes.")
    uploaded_at: int = Field(
        default_factory=current_timestamp_int, description="Unix timestamp when the file was uploaded."
    )
    updated_at: int = Field(
        default_factory=current_timestamp_int, description="Unix timestamp when the file was last updated."
    )

    @property
    def filepath(self) -> Path:
        """Get the full file path relative to the server storage directory."""
        return self.parent_directory / self.filename


# API Response Models
class ListFilesResponse(BaseResponse):
    """Response model for getting metadata for all files."""

    model_config = ConfigDict(populate_by_name=True)

    files_metadata: list[FileMetadata] = Field(..., description="The metadata of all files.", alias="filesMetadata")


class UploadFileResponse(BaseResponse):
    """Response model for uploading a file."""

    model_config = ConfigDict(populate_by_name=True)

    file_metadata: FileMetadata = Field(..., description="The metadata of the uploaded file.", alias="fileMetadata")


class DeleteFileResponse(BaseResponse):
    """Response model for deleting a file."""

    model_config = ConfigDict(populate_by_name=True)

    file_metadata: FileMetadata = Field(..., description="The metadata of the deleted file.", alias="fileMetadata")


class GetFileMetadataResponse(BaseResponse):
    """Response model for getting file metadata."""

    model_config = ConfigDict(populate_by_name=True)

    file_metadata: FileMetadata = Field(..., description="The metadata of the retrieved file.", alias="fileMetadata")


class UpdateFileMetadataResponse(BaseResponse):
    """Response model for updating file metadata."""

    model_config = ConfigDict(populate_by_name=True)

    file_metadata: FileMetadata = Field(..., description="The metadata of the updated file.", alias="fileMetadata")


# API Request Models
class UpdateFileMetadataRequest(BaseModel):
    """Request model for updating file metadata."""

    model_config = ConfigDict(populate_by_name=True)

    filename: str = Field(..., description="New filename for the file.")
    parent_directory: Path = Field(
        ..., description="New parent directory path relative to server storage directory.", alias="parentDirectory"
    )
