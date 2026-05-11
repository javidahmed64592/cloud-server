"""Authentication handler for the server."""

import hashlib
import logging
import secrets

from template_python.logging_setup import setup_default_logging

from python_template_server.constants import ENV_FILE_PATH, TOKEN_ENV_VAR_NAME, TOKEN_LENGTH

setup_default_logging()
logger = logging.getLogger(__name__)


def generate_token() -> str:
    """Generate a secure random token.

    :return str: A URL-safe token string
    """
    return secrets.token_urlsafe(TOKEN_LENGTH)


def hash_token(token: str) -> str:
    """Hash a token string using SHA-256.

    :param str token: The plain text token to hash
    :return str: The hexadecimal representation of the hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def save_hashed_token(token: str) -> None:
    """Hash a token and save it to the .env file.

    :param str token: The plain text token to hash and save
    """
    hashed = hash_token(token)

    if not ENV_FILE_PATH.exists():
        ENV_FILE_PATH.touch()

    content = ENV_FILE_PATH.read_text()
    lines = content.splitlines(keepends=True)
    new_lines = []
    for line in lines:
        if line.startswith(f"{TOKEN_ENV_VAR_NAME}="):
            new_lines.append(f"{TOKEN_ENV_VAR_NAME}={hashed}\n")
        else:
            new_lines.append(line)
    ENV_FILE_PATH.write_text("".join(new_lines))


def verify_token(token: str, hashed_token: str) -> bool:
    """Verify a token against the stored hash.

    :param str token: The plain text token to verify
    :param str hashed_token: The stored hashed token for comparison
    :return bool: True if the token matches the stored hash, False otherwise
    """
    if not hashed_token:
        msg = "No stored token hash found for verification."
        raise ValueError(msg)

    return hash_token(token) == hashed_token


def generate_new_token() -> None:
    """Generate a new token, hash it, and save the hash to the .env file.

    This function generates a new secure random token, hashes it using SHA-256,
    and saves the hashed token to the .env file for future verification.
    """
    new_token = generate_token()
    save_hashed_token(new_token)
    logger.info("New API token generated and saved.")
    print(f"Token: {new_token}")  # Prevent logging token to log file
