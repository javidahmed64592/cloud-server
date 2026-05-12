"""Pi Dashboard server module."""

import logging
from pathlib import Path

from python_template_server.constants import ROOT_DIR
from python_template_server.template_server import BaseRouter, TemplateServer

from cloud_server.db import FilesMetadataDatabaseManager
from cloud_server.models import CloudServerConfig
from cloud_server.routers import FilesRouter

logger = logging.getLogger(__name__)

FILES_ROUTER = FilesRouter(prefix="/files")


class CloudServer(TemplateServer):
    """Cloud FastAPI server."""

    def __init__(self, config: CloudServerConfig | None = None) -> None:
        """Initialize the CloudServer.

        :param CloudServerConfig | None config: Optional pre-loaded configuration
        """
        self.files_metadata_database_manager = FilesMetadataDatabaseManager()

        self.config: CloudServerConfig
        super().__init__(
            package_name="cloud-server",
            config=config,
        )
        logger.info("Initializing CloudServer...")

        logger.info("Creating server directory: %s", self.server_directory)
        self.server_directory.mkdir(parents=True, exist_ok=True)

        logger.info("Creating storage directory: %s", self.storage_directory)
        self.storage_directory.mkdir(parents=True, exist_ok=True)

        self.files_metadata_database_manager.configure(db_config=self.config.db)

    @property
    def server_directory(self) -> Path:
        """Get the server directory path."""
        return Path(ROOT_DIR) / "server"

    @property
    def storage_directory(self) -> Path:
        """Get the storage directory path."""
        return self.server_directory / "storage"

    @property
    def routers(self) -> list[BaseRouter]:
        """Define the API routers for the server.

        :return list[BaseRouter]: List of API routers
        """
        FILES_ROUTER.configure_router(db=self.files_metadata_database_manager, storage_directory=self.storage_directory)
        return [FILES_ROUTER]

    def validate_config(self, config_data: dict) -> CloudServerConfig:
        """Validate configuration data against the CloudServerConfig model.

        :param dict config_data: The configuration data to validate
        :return CloudServerConfig: The validated configuration model
        """
        return CloudServerConfig.model_validate(config_data)  # type: ignore[no-any-return]
