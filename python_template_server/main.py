"""FastAPI template server using uvicorn."""

from pathlib import Path
from typing import Any

from python_template_server.constants import CONFIG_FILE_PATH, STATIC_DIR
from python_template_server.models import TemplateServerConfig
from python_template_server.routers import BaseRouter
from python_template_server.template_server import TemplateServer


class ExampleServer(TemplateServer):
    """Example server inheriting from TemplateServer."""

    def __init__(
        self,
        config_filepath: Path = CONFIG_FILE_PATH,
        config: TemplateServerConfig | None = None,
        static_dir: Path = STATIC_DIR,
    ) -> None:
        """Initialize the ExampleServer by delegating to the template server.

        :param TemplateServerConfig config: Configuration object
        :param Path config_filepath: Configuration filepath
        :param Path static_dir: Static files directory
        """
        super().__init__(config=config, config_filepath=config_filepath, static_dir=static_dir)

    @property
    def routers(self) -> list[BaseRouter]:
        """Define the API routers for the server.

        :return list[BaseRouter]: List of API routers
        """
        return []

    def validate_config(self, config_data: dict[str, Any]) -> TemplateServerConfig:
        """Validate configuration from the config.json file.

        :return TemplateServerConfig: Loaded configuration
        """
        return super().validate_config(config_data)


def run() -> None:
    """Serve the FastAPI application using uvicorn.

    :raise SystemExit: If configuration fails to load or SSL certificate files are missing
    """
    server = ExampleServer()
    server.run()
