"""SQLModel database module."""

import logging
from abc import ABC, abstractmethod

from sqlmodel import SQLModel, create_engine

from python_template_server.models import DatabaseConfig

logger = logging.getLogger(__name__)


class BaseDatabaseManager(ABC):
    """Manager class for database operations.

    Subclasses must implement the `db_url` property to provide the correct database URL.
    The database manager must be configured using `configure()` after the server has loaded the configuration.
    """

    def __init__(self) -> None:
        """Initialize the database manager."""
        logger.info("Ready to be configured...")

    def configure(self, db_config: DatabaseConfig) -> None:
        """Configure the database manager with the given configuration."""
        self.db_config = db_config
        self.db_config.db_directory.mkdir(parents=True, exist_ok=True)

        logger.info("Initializing database with URL: %s", self.db_url)
        self.engine = create_engine(self.db_url, echo=False)
        SQLModel.metadata.create_all(self.engine)

    @property
    @abstractmethod
    def db_url(self) -> str:
        """Get the database URL using the `DatabaseConfig.db_url()` method."""
