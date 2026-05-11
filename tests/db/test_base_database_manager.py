"""Unit tests for the python_template_server.db.base_database_manager module."""

from collections.abc import Generator

import pytest
from sqlalchemy import Engine

from python_template_server.db import BaseDatabaseManager
from python_template_server.models import DatabaseConfig

MOCK_DB_FILENAME = "test.db"


class MockDatabaseManager(BaseDatabaseManager):
    """Mock implementation of BaseDatabaseManager for testing."""

    @property
    def db_url(self) -> str:
        """Return a mock database URL."""
        return self.db_config.db_url(MOCK_DB_FILENAME)


@pytest.fixture
def mock_database_manager(mock_db_config: DatabaseConfig) -> Generator[BaseDatabaseManager]:
    """Fixture for creating a mock database manager."""
    db_manager = MockDatabaseManager()
    db_manager.configure(mock_db_config)
    yield db_manager
    db_manager.engine.dispose()


class TestBaseDatabaseManager:
    """Unit tests for the BaseDatabaseManager class."""

    def test_configuration(self, mock_database_manager: BaseDatabaseManager) -> None:
        """Test that the database manager is configured correctly."""
        assert isinstance(mock_database_manager.db_config, DatabaseConfig)
        assert isinstance(mock_database_manager.engine, Engine)

    def test_db_url_property(self, mock_database_manager: BaseDatabaseManager) -> None:
        """Test that the db_url property returns the correct URL."""
        expected_url = mock_database_manager.db_config.db_url(MOCK_DB_FILENAME)
        assert mock_database_manager.db_url == expected_url
