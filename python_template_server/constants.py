"""Constants used across the server."""

from pathlib import Path

from pyhere import here

# Logging constants
MB_TO_BYTES = 1024 * 1024
LOGGING_MAX_BYTES_MB = 10
LOGGING_BACKUP_COUNT = 5

# File system constants
ROOT_DIR = Path(here())
CONFIG_DIR = ROOT_DIR / "configuration"
LOGGING_DIR = ROOT_DIR / "logs"
STATIC_DIR = ROOT_DIR / "static"

CONFIG_FILE_PATH = CONFIG_DIR / "config.json"
LOGGING_FILE_PATH = LOGGING_DIR / "server.log"
ENV_FILE_PATH = ROOT_DIR / ".env"

# API constants
API_PREFIX = "/api"
API_KEY_HEADER_NAME = "X-API-Key"

# Authentication constants
TOKEN_ENV_VAR_NAME = "API_TOKEN_HASH"  # noqa: S105
TOKEN_LENGTH = 32
