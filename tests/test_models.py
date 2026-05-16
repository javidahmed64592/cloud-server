"""Unit tests for the cloud_server.models module."""

from cloud_server.models import CloudServerConfig, FileMetadata


# Cloud Server Configuration Models
class TestCloudServerConfig:
    """Unit tests for the CloudServerConfig class."""

    def test_model_dump(
        self,
        mock_cloud_server_config: CloudServerConfig,
        mock_db_config_dict: dict,
        mock_storage_config_dict: dict,
    ) -> None:
        """Test the model_dump method."""
        dumped_model = mock_cloud_server_config.model_dump()
        assert dumped_model["db"] == mock_db_config_dict
        assert dumped_model["storage_config"] == mock_storage_config_dict


# File Models
class TestFileMetadata:
    """Unit tests for the FileMetadata class."""

    def test_timestamps(self, mock_file_metadata: FileMetadata) -> None:
        """Test the timestamps of the FileMetadata model."""
        assert isinstance(mock_file_metadata.uploaded_at, int)
        assert mock_file_metadata.uploaded_at > 0

        assert isinstance(mock_file_metadata.updated_at, int)
        assert mock_file_metadata.updated_at > 0

    def test_filepath(self, mock_file_metadata: FileMetadata) -> None:
        """Test the filepath property."""
        expected_path = mock_file_metadata.parent_directory / mock_file_metadata.filename
        assert mock_file_metadata.filepath == expected_path
