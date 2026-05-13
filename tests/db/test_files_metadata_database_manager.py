"""Unit tests for the cloud_server.db.files_metadata_database_manager module."""

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

from cloud_server.db import FilesMetadataDatabaseManager
from cloud_server.models import DatabaseAction, FileMetadata


class TestFilesMetadataDatabaseManager:
    """Tests for the FilesMetadataDatabaseManager class."""

    @pytest.fixture
    def mock_session(self) -> Session:
        """Provide a mock SQLAlchemy session."""
        return MagicMock(spec=Session)

    def test_init_creates_database(self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager) -> None:
        """Test FilesMetadataDatabaseManager initialization creates the database directory and file."""
        assert isinstance(mock_files_metadata_database_manager.engine, Engine)

    def test_create_file_metadata_with_id(
        self,
        mock_files_metadata_database_manager: FilesMetadataDatabaseManager,
        mock_session: Session,
        mock_file_metadata: FileMetadata,
    ) -> None:
        """Test adding file metadata with an ID raises an error."""
        mock_file_metadata.id = 1
        with pytest.raises(ValueError, match=f"File metadata ID must be None for new entries: {mock_file_metadata.id}"):
            mock_files_metadata_database_manager._create_file_metadata(
                session=mock_session, file_metadata=mock_file_metadata
            )

    def test_read_nonexistent_file_metadata(
        self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager, mock_session: Session
    ) -> None:
        """Test reading file metadata for a non-existent ID raises an error."""
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="File for ID not found: 999"):
            mock_files_metadata_database_manager._read_file_metadata(session=mock_session, file_id=999)

    def test_update_nonexistent_file_metadata(
        self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager, mock_session: Session
    ) -> None:
        """Test updating file metadata for a non-existent ID raises an error."""
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="File for ID not found: 999"):
            mock_files_metadata_database_manager._update_file_metadata(
                session=mock_session, file_id=999, file_metadata=MagicMock(spec=FileMetadata)
            )

    def test_delete_nonexistent_file_metadata(
        self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager, mock_session: Session
    ) -> None:
        """Test deleting file metadata for a non-existent ID raises an error."""
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="File for ID not found: 999"):
            mock_files_metadata_database_manager._delete_file_metadata(session=mock_session, file_id=999)

    def test_list_files(self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager) -> None:
        """Test listing files metadata returns a list."""
        files = mock_files_metadata_database_manager.list_files()
        assert isinstance(files, list)
        assert len(files) > 0
        assert all(isinstance(file, FileMetadata) for file in files)

    def test_perform_file_metadata_action(
        self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager, mock_file_metadata: FileMetadata
    ) -> None:
        """Test performing file metadata actions (CRUD)."""
        num_files = len(mock_files_metadata_database_manager.list_files())

        # Test CREATE action
        created_metadata = mock_files_metadata_database_manager.perform_file_metadata_action(
            action=DatabaseAction.CREATE,
            file_metadata=mock_file_metadata,
        )
        assert created_metadata.id is not None
        assert created_metadata.filepath == mock_file_metadata.filepath
        assert len(mock_files_metadata_database_manager.list_files()) == num_files + 1

        # Test READ action
        read_metadata = mock_files_metadata_database_manager.perform_file_metadata_action(
            action=DatabaseAction.READ,
            file_id=created_metadata.id,
        )
        assert read_metadata.id == created_metadata.id
        assert read_metadata.filepath == created_metadata.filepath

        # Test UPDATE action
        updated_filename = "updated_test_file.txt"
        time.sleep(1)
        updated_metadata = mock_files_metadata_database_manager.perform_file_metadata_action(
            action=DatabaseAction.UPDATE,
            file_id=created_metadata.id,
            file_metadata=FileMetadata(
                id=created_metadata.id,
                filename=updated_filename,
                parent_directory=created_metadata.parent_directory,
                mime_type=created_metadata.mime_type,
                size=created_metadata.size,
            ),
        )
        assert updated_metadata.id == created_metadata.id
        assert updated_metadata.filename == updated_filename
        assert updated_metadata.parent_directory == created_metadata.parent_directory
        assert updated_metadata.updated_at > created_metadata.updated_at

        # Test DELETE action
        deleted_metadata = mock_files_metadata_database_manager.perform_file_metadata_action(
            action=DatabaseAction.DELETE,
            file_id=created_metadata.id,
        )
        assert deleted_metadata.id == created_metadata.id
        assert len(mock_files_metadata_database_manager.list_files()) == num_files

    def test_perform_file_metadata_action_invalid_parameters(
        self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager
    ) -> None:
        """Test performing file metadata action with missing parameters raises an error."""
        with pytest.raises(ValueError, match=r"Missing parameters:"):
            mock_files_metadata_database_manager.perform_file_metadata_action(action=DatabaseAction.CREATE)

    def test_synchronize_with_storage(
        self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager, mock_tmp_storage_path: Path
    ) -> None:
        """Test synchronizing the database with the storage directory."""
        new_file_path = mock_tmp_storage_path / "new_test_file_1.txt"
        new_file_path.write_text("New test file content")

        new_metadata = FileMetadata(
            id=None,
            filename="new_test_file_2.txt",
            parent_directory=Path("."),
            mime_type="text/plain",
            size=2048,
        )
        mock_files_metadata_database_manager.perform_file_metadata_action(
            action=DatabaseAction.CREATE,
            file_metadata=new_metadata,
        )

        mock_files_metadata_database_manager.synchronize_with_storage(storage_directory=mock_tmp_storage_path)

        files = mock_files_metadata_database_manager.list_files()
        filepaths = [file.filepath for file in files]
        assert Path("new_test_file_1.txt") in filepaths
        assert Path("new_test_file_2.txt") not in filepaths

    def test_synchronize_with_empty_storage_directory(
        self, mock_files_metadata_database_manager: FilesMetadataDatabaseManager, tmp_path: Path
    ) -> None:
        """Test synchronizing with an empty storage directory does not modify the database."""
        empty_dir = tmp_path / "empty_storage"
        empty_dir.mkdir()
        mock_files_metadata_database_manager.synchronize_with_storage(storage_directory=empty_dir)
        files = mock_files_metadata_database_manager.list_files()
        assert isinstance(files, list)
        assert len(files) > 0
        assert all(isinstance(file, FileMetadata) for file in files)
