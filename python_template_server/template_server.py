"""Template FastAPI server module."""

import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import metadata
from pathlib import Path
from typing import Any

import dotenv
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic_core import ValidationError
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException
from template_python.logging_setup import add_file_handler, setup_default_logging

from python_template_server.certificate_handler import CertificateHandler
from python_template_server.constants import (
    API_KEY_HEADER_NAME,
    API_PREFIX,
    CONFIG_FILE_PATH,
    ENV_FILE_PATH,
    LOGGING_BACKUP_COUNT,
    LOGGING_FILE_PATH,
    LOGGING_MAX_BYTES_MB,
    MB_TO_BYTES,
    STATIC_DIR,
    TOKEN_ENV_VAR_NAME,
)
from python_template_server.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from python_template_server.models import (
    CustomJSONResponse,
    ResponseCode,
    TemplateServerConfig,
)
from python_template_server.routers import BaseRouter, TemplateServerRouter

dotenv.load_dotenv(ENV_FILE_PATH)
setup_default_logging()
add_file_handler(
    logging_filepath=LOGGING_FILE_PATH,
    max_bytes=LOGGING_MAX_BYTES_MB * MB_TO_BYTES,
    backup_count=LOGGING_BACKUP_COUNT,
)
logger = logging.getLogger(__name__)


TEMPLATE_SERVER_ROUTER = TemplateServerRouter(prefix="")


class TemplateServer(ABC):
    """Template FastAPI server.

    This class provides a template for building FastAPI servers with common features
    such as request logging, security headers and rate limiting.

    Ensure you implement the `routers` property and `validate_config` method in subclasses.
    """

    def __init__(
        self,
        package_name: str = "python-template-server",
        api_prefix: str = API_PREFIX,
        api_key_header_name: str = API_KEY_HEADER_NAME,
        config_filepath: Path = CONFIG_FILE_PATH,
        config: TemplateServerConfig | None = None,
        static_dir: Path = STATIC_DIR,
    ) -> None:
        """Initialize the TemplateServer.

        :param str api_prefix: The API prefix for the server
        :param str api_key_header_name: The API key header name
        :param Path config_filepath: Path to the configuration file
        :param TemplateServerConfig | None config: Optional pre-loaded configuration
        """
        self.api_prefix = api_prefix
        self.api_key_header_name = api_key_header_name
        self.config_filepath = config_filepath
        self.config = config or self.load_config(self.config_filepath)
        self.cert_handler = CertificateHandler(self.config.certificate)
        self.static_dir = static_dir

        logger.info("Configuring FastAPI server...")
        CustomJSONResponse.configure(self.config.json_response)
        self.package_metadata = metadata(package_name)
        self.app = FastAPI(
            title=self.package_metadata["Name"],
            description=self.package_metadata["Summary"],
            version=self.package_metadata["Version"],
            root_path=self.api_prefix,
            lifespan=self.lifespan,
            default_response_class=CustomJSONResponse,
        )
        self.api_key_header = APIKeyHeader(name=self.api_key_header_name, auto_error=False)

        logger.info("Loading environment variables...")
        self.host = os.getenv("HOST", "localhost")
        self.port = int(os.getenv("PORT", "443"))

        if not (hashed_token := os.getenv(TOKEN_ENV_VAR_NAME)):
            error_msg = "Server token is not configured. Set the token using: uv run generate-new-token"
            logger.error(error_msg)
            raise HTTPException(
                status_code=ResponseCode.INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )
        self.hashed_token = hashed_token

        logger.info("Setting up server features...")
        self._setup_request_logging()
        self._setup_security_headers()
        self._setup_cors()
        self._setup_rate_limiting()
        self._setup_routes()
        logger.info("Template server initialization complete!")

    @staticmethod
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """Handle application lifespan events."""
        yield

    @property
    def static_dir_exists(self) -> bool:
        """Check if the static directory exists.

        :return bool: True if the static directory exists, False otherwise
        """
        return self.static_dir.exists() and (self.static_dir / "index.html").exists()

    @property
    @abstractmethod
    def routers(self) -> list[BaseRouter]:
        """List of BaseRouter instances to include in the server.

        :return list[BaseRouter]: List of BaseRouter instances
        """
        return []

    @abstractmethod
    def validate_config(self, config_data: dict[str, Any]) -> TemplateServerConfig:
        """Validate configuration data against the TemplateServerConfig model.

        :param dict config_data: The configuration data to validate
        :return TemplateServerConfig: The validated configuration model
        :raise ValidationError: If the configuration data is invalid
        """
        return TemplateServerConfig.model_validate(config_data)

    def load_config(self, config_filepath: Path) -> TemplateServerConfig:
        """Load configuration from the specified json file.

        :param Path config_filepath: Path to the configuration file
        :return TemplateServerConfig: The validated configuration model
        :raise SystemExit: If configuration file is missing, invalid JSON, or fails validation
        """
        if not config_filepath.exists():
            logger.error("Configuration file not found: %s", config_filepath)
            sys.exit(1)

        try:
            logger.info("Loading configuration from: %s", config_filepath)
            config_data = json.loads(config_filepath.read_text(encoding="utf-8"))
            config = self.validate_config(config_data)
            config.save_to_file(config_filepath)
        except json.JSONDecodeError:
            logger.exception("JSON parsing error: %s", config_filepath)
            sys.exit(1)
        except OSError:
            logger.exception("JSON read error: %s", config_filepath)
            sys.exit(1)
        except ValidationError:
            logger.exception("Invalid configuration in: %s", config_filepath)
            sys.exit(1)
        else:
            return config

    def _setup_request_logging(self) -> None:
        """Set up request logging middleware."""
        self.app.add_middleware(RequestLoggingMiddleware)
        logger.info("Request logging: ENABLED")

    def _setup_security_headers(self) -> None:
        """Set up security headers middleware."""
        self.app.add_middleware(
            SecurityHeadersMiddleware,
            hsts_max_age=self.config.security.hsts_max_age,
            csp=self.config.security.content_security_policy,
        )

        logger.info(
            "Security headers: ENABLED | HSTS max-age=%s, CSP=%s",
            self.config.security.hsts_max_age,
            self.config.security.content_security_policy,
        )

    def _setup_cors(self) -> None:
        """Set up CORS middleware."""
        if not self.config.cors.enabled:
            logger.info("CORS: DISABLED")
            return

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors.allow_origins,
            allow_credentials=self.config.cors.allow_credentials,
            allow_methods=self.config.cors.allow_methods,
            allow_headers=self.config.cors.allow_headers,
            expose_headers=self.config.cors.expose_headers,
            max_age=self.config.cors.max_age,
        )

        logger.info(
            "CORS: ENABLED | origins=%s, credentials=%s, methods=%s, headers=%s",
            self.config.cors.allow_origins,
            self.config.cors.allow_credentials,
            self.config.cors.allow_methods,
            self.config.cors.allow_headers,
        )

    async def _rate_limit_exception_handler(self, request: Request, exc: RateLimitExceeded) -> CustomJSONResponse:
        """Handle rate limit exceeded exceptions.

        :param Request request: The incoming HTTP request
        :param RateLimitExceeded exc: The rate limit exceeded exception
        :return JSONResponse: HTTP 429 JSON response
        """
        logger.warning("Rate limit exceeded for: %s", request.url.path)
        return CustomJSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(exc.retry_after)} if hasattr(exc, "retry_after") else {},
        )

    def _setup_rate_limiting(self) -> None:
        """Set up rate limiting middleware."""
        if not self.config.rate_limit.enabled:
            logger.info("Rate limiting: DISABLED")
            self.limiter = None
            return

        self.limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=self.config.rate_limit.storage_uri,
        )

        self.app.state.limiter = self.limiter
        self.app.add_exception_handler(RateLimitExceeded, self._rate_limit_exception_handler)  # type: ignore[arg-type]

        logger.info(
            "Rate limiting: ENABLED | rate=%s, storage=%s",
            self.config.rate_limit.rate_limit,
            self.config.rate_limit.storage_uri or "in-memory",
        )

    async def _custom_404_handler(self, request: Request, exc: StarletteHTTPException) -> Response:
        """Handle 404 errors by serving custom 404.html if available."""
        if exc.status_code == ResponseCode.NOT_FOUND and self.static_dir_exists:
            if (not_found_page := self.static_dir / "404.html").is_file():
                return FileResponse(not_found_page, status_code=ResponseCode.NOT_FOUND)
        raise exc

    def _setup_routes(self) -> None:
        """Set up API routes."""
        routers: list[BaseRouter] = [TEMPLATE_SERVER_ROUTER, *self.routers]
        for router in routers:
            router.configure(self.hashed_token, self.limiter, self.config.rate_limit.rate_limit)
            router.setup_routes()
            self.app.include_router(router.router)

        if self.static_dir_exists:
            logger.info("Mounting static directory: %s", self.static_dir)
            self.app.mount("/", StaticFiles(directory=self.static_dir, html=True), name="static")
            self.app.add_exception_handler(StarletteHTTPException, self._custom_404_handler)  # type: ignore[arg-type]

    def run(self) -> None:
        """Run the server using uvicorn."""
        try:
            cert_file = self.config.certificate.ssl_cert_file_path
            key_file = self.config.certificate.ssl_key_file_path

            if not (cert_file.exists() and key_file.exists()):
                logger.warning("SSL certificate or key file not found, generating self-signed certificate...")
                self.cert_handler.generate_self_signed_cert()

            logger.info("Starting server: https://%s:%s%s", self.host, self.port, self.api_prefix)
            uvicorn.run(
                app=self.app,
                host=self.host,
                port=self.port,
                ssl_keyfile=str(key_file),
                ssl_certfile=str(cert_file),
                log_level="warning",
                access_log=False,
            )
            logger.info("Server stopped.")
        except Exception:
            logger.exception("Failed to start!")
            sys.exit(1)
