"""Pydantic models for the server."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field
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
    UPDATE = "update"
    DELETE = "delete"
    GET = "get"


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


# API Response Models
class GetFilesMetadataResponse(BaseResponse):
    """Response model for getting metadata for all files."""

    files_metadata: list[FileMetadata] = Field(..., description="The metadata of all files.", alias="filesMetadata")


class AddFileMetadataResponse(BaseResponse):
    """Response model for adding file metadata."""

    file_metadata: FileMetadata = Field(..., description="The metadata of the added file.", alias="fileMetadata")


class UpdateFileMetadataResponse(BaseResponse):
    """Response model for updating file metadata."""

    file_metadata: FileMetadata = Field(..., description="The metadata of the updated file.", alias="fileMetadata")


class DeleteFileMetadataResponse(BaseResponse):
    """Response model for deleting file metadata."""

    file_metadata: FileMetadata = Field(..., description="The metadata of the deleted file.", alias="fileMetadata")


class GetFileMetadataResponse(BaseResponse):
    """Response model for getting file metadata."""

    file_metadata: FileMetadata = Field(..., description="The metadata of the retrieved file.", alias="fileMetadata")
