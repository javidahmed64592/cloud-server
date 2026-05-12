"""Unit tests for the cloud_server.main module."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from cloud_server.main import run
from cloud_server.server import CloudServer


@pytest.fixture
def mock_server_class() -> Generator[CloudServer]:
    """Mock CloudServer class."""
    with patch("cloud_server.main.CloudServer", autospec=True) as mock_server:
        yield mock_server


class TestRun:
    """Unit tests for the run function."""

    def test_run(self, mock_server_class: CloudServer) -> None:
        """Test successful server run."""
        run()

        mock_server_class.return_value.run.assert_called_once()
