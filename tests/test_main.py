"""Unit tests for the python_template_server.main module."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from python_template_server.main import run
from python_template_server.models import TemplateServerConfig


@pytest.fixture
def mock_template_server_class(mock_template_server_config: TemplateServerConfig) -> Generator[MagicMock]:
    """Mock TemplateServer class."""
    with patch("python_template_server.main.ExampleServer") as mock_server:
        mock_server.load_config.return_value = mock_template_server_config
        yield mock_server


class TestRun:
    """Unit tests for the run function."""

    def test_run(self, mock_template_server_class: MagicMock) -> None:
        """Test successful server run."""
        run()

        mock_template_server_class.return_value.run.assert_called_once()
