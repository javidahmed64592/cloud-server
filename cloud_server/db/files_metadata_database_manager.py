"""Files metadata database manager."""

import logging
import mimetypes
from pathlib import Path

from python_template_server.db import BaseDatabaseManager
from sqlmodel import Field, Session, SQLModel, select

from cloud_server.models import DatabaseAction, FileMetadata, ServerDatabaseConfig, current_timestamp_int

logger = logging.getLogger(__name__)


# Database table models
class FileMetadataDB(SQLModel, table=True):
    """Files metadata table."""

    __tablename__ = "files_metadata"

    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(..., description="Original filename of the uploaded file.")
    parent_directory: str = Field(..., description="Path to parent directory relative to server storage directory.")
    mime_type: str = Field(..., description="MIME type of the file.")
    size: int = Field(..., description="File size in bytes.")
    uploaded_at: int = Field(
        default_factory=current_timestamp_int, description="Unix timestamp when the file was uploaded."
    )
    updated_at: int = Field(
        default_factory=current_timestamp_int, description="Unix timestamp when the file was last updated."
    )

    @classmethod
    def from_file_metadata(cls, file_metadata: FileMetadata) -> "FileMetadataDB":
        """Create a FileMetadataDB instance from a FileMetadata."""
        return cls(
            id=file_metadata.id,
            filename=file_metadata.filename,
            parent_directory=str(file_metadata.parent_directory),
            mime_type=file_metadata.mime_type,
            size=file_metadata.size,
            uploaded_at=file_metadata.uploaded_at,
            updated_at=file_metadata.updated_at,
        )

    def to_file_metadata(self) -> FileMetadata:
        """Convert the database model to a FileMetadata."""
        return FileMetadata(
            id=self.id,
            filename=self.filename,
            parent_directory=Path(self.parent_directory),
            mime_type=self.mime_type,
            size=self.size,
            uploaded_at=self.uploaded_at,
            updated_at=self.updated_at,
        )

    def update_from_file_metadata(self, file_metadata: FileMetadata) -> None:
        """Update the database model fields from a FileMetadata."""
        self.filename = file_metadata.filename or self.filename
        self.parent_directory = str(file_metadata.parent_directory) or self.parent_directory
        self.updated_at = current_timestamp_int()


# Database manager class
class FilesMetadataDatabaseManager(BaseDatabaseManager):
    """Manager class for files metadata database operations."""

    def __init__(self) -> None:
        """Initialize the FilesMetadataDatabaseManager with the given database configuration."""
        self.db_config: ServerDatabaseConfig
        super().__init__()

    @property
    def db_url(self) -> str:
        """Get the database URL."""
        return self.db_config.db_url(self.db_config.files_metadata_db_filename)  # type: ignore[no-any-return]

    def _create_file_metadata(self, session: Session, file_metadata: FileMetadata) -> FileMetadata:
        """Add a new file metadata entry to the database."""
        if file_metadata.id is not None:
            error_msg = f"File metadata ID must be None for new entries, got ID {file_metadata.id}!"
            logger.error(error_msg)
            raise ValueError(error_msg)

        db_entry = FileMetadataDB.from_file_metadata(file_metadata=file_metadata)
        session.add(db_entry)
        session.commit()
        session.refresh(db_entry)
        return db_entry.to_file_metadata()

    def _read_file_metadata(self, session: Session, file_id: int) -> FileMetadata:
        """Retrieve a file metadata entry from the database."""
        if not (db_entry := session.get(FileMetadataDB, file_id)):
            error_msg = f"File {file_id} not found!"
            logger.error(error_msg)
            raise ValueError(error_msg)

        return db_entry.to_file_metadata()

    def _update_file_metadata(self, session: Session, file_id: int, file_metadata: FileMetadata) -> FileMetadata:
        """Update an existing file metadata entry in the database."""
        if not (db_entry := session.get(FileMetadataDB, file_id)):
            error_msg = f"File {file_id} not found!"
            logger.error(error_msg)
            raise ValueError(error_msg)

        db_entry.update_from_file_metadata(file_metadata=file_metadata)
        session.add(db_entry)
        session.commit()
        session.refresh(db_entry)
        return db_entry.to_file_metadata()

    def _delete_file_metadata(self, session: Session, file_id: int) -> FileMetadata:
        """Delete a file metadata entry from the database."""
        if not (db_entry := session.get(FileMetadataDB, file_id)):
            error_msg = f"File {file_id} not found!"
            logger.error(error_msg)
            raise ValueError(error_msg)

        session.delete(db_entry)
        session.commit()
        return db_entry.to_file_metadata()

    def _list_files_metadata(self, session: Session) -> list[FileMetadata]:
        """List all file metadata entries in the database."""
        db_entries = session.exec(select(FileMetadataDB)).all()
        return [db_entry.to_file_metadata() for db_entry in db_entries]

    def list_files(self) -> list[FileMetadata]:
        """Public method to list all file metadata entries."""
        with Session(self.engine) as session:
            return self._list_files_metadata(session=session)

    def perform_file_metadata_action(
        self, action: DatabaseAction, file_metadata: FileMetadata | None = None, file_id: int | None = None
    ) -> FileMetadata:
        """Perform a database action (CRUD) on file metadata."""
        with Session(self.engine) as session:
            match action:
                case DatabaseAction.CREATE if file_metadata is not None:
                    return self._create_file_metadata(session=session, file_metadata=file_metadata)
                case DatabaseAction.READ if file_id is not None:
                    return self._read_file_metadata(session=session, file_id=file_id)
                case DatabaseAction.UPDATE if file_id is not None and file_metadata is not None:
                    return self._update_file_metadata(session=session, file_id=file_id, file_metadata=file_metadata)
                case DatabaseAction.DELETE if file_id is not None:
                    return self._delete_file_metadata(session=session, file_id=file_id)
                case _:
                    error_msg = f"Missing parameters: action={action}, file_id={file_id}, file_metadata={file_metadata}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

    def synchronize_with_storage(self, storage_directory: Path) -> None:
        """Synchronize the files metadata database with the actual files in the storage directory.

        This method ensures that the database entries accurately reflect the files present in the storage directory.
        It adds metadata for new files, updates metadata for existing files, and removes metadata for deleted files.

        :param Path storage_directory: The path to the storage directory to synchronize with
        """
        if not any(storage_directory.iterdir()):
            logger.warning("Storage directory is empty, skipping synchronization: %s", storage_directory)
            return

        existing_metadata = {metadata.filepath: metadata for metadata in self.list_files()}

        for filepath in storage_directory.rglob("*"):
            if filepath.is_file():
                relative_path = filepath.relative_to(storage_directory)
                if relative_path.parts[0] == ".thumbnails":
                    continue

                if relative_path in existing_metadata.keys():
                    del existing_metadata[relative_path]
                    continue

                filename = relative_path.name
                parent_directory = relative_path.parent
                mime_type, _ = mimetypes.guess_type(filepath)
                size = filepath.stat().st_size

                file_metadata = FileMetadata(
                    filename=filename,
                    parent_directory=parent_directory,
                    mime_type=mime_type or "application/octet-stream",
                    size=size,
                )

                logger.info("Adding new metadata for file: %s", file_metadata.filepath)
                self.perform_file_metadata_action(action=DatabaseAction.CREATE, file_metadata=file_metadata)

        for remaining_entry in existing_metadata.values():
            logger.warning("Removing metadata for deleted file: %s", remaining_entry.filepath)
            self.perform_file_metadata_action(action=DatabaseAction.DELETE, file_id=remaining_entry.id)
