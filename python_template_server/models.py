"""Pydantic models for the server."""

import json
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# Template Server Configuration Models
class SecurityConfigModel(BaseModel):
    """Security headers configuration model."""

    hsts_max_age: int = Field(default=31536000, ge=0, description="HSTS max-age in seconds (1 year default)")
    content_security_policy: str = Field(
        default=(
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://cdn.jsdelivr.net https://fastapi.tiangolo.com"
        ),
        description="Content Security Policy header value",
    )


class CORSConfigModel(BaseModel):
    """CORS (Cross-Origin Resource Sharing) configuration model."""

    enabled: bool = Field(default=False, description="Whether CORS is enabled")
    allow_origins: list[str] = Field(default_factory=lambda: ["*"], description="List of allowed origins")
    allow_credentials: bool = Field(default=True, description="Whether to allow credentials")
    allow_methods: list[str] = Field(default_factory=lambda: ["GET"], description="List of allowed HTTP methods")
    allow_headers: list[str] = Field(
        default_factory=lambda: ["Content-Type", "X-API-Key"], description="List of allowed headers"
    )
    expose_headers: list[str] = Field(default_factory=list, description="List of headers to expose")
    max_age: int = Field(default=600, ge=0, description="Maximum age (in seconds) for CORS preflight cache")


class RateLimitConfigModel(BaseModel):
    """Rate limit configuration model."""

    enabled: bool = Field(default=True, description="Whether rate limiting is enabled")
    rate_limit: str = Field(default="100/minute", description="Rate limit for API endpoints (format: count/period)")
    storage_uri: str = Field(default="", description="Storage URI for rate limit data (empty string for in-memory)")


class CertificateConfigModel(BaseModel):
    """Certificate configuration model."""

    directory: str = Field(default="certs", description="Directory where SSL certificate and key files are stored")
    ssl_keyfile: str = Field(default="key.pem", description="Filename of the SSL key file")
    ssl_certfile: str = Field(default="cert.pem", description="Filename of the SSL certificate file")
    days_valid: int = Field(default=365, ge=1, description="Number of days the certificate is valid")

    @property
    def ssl_key_file_path(self) -> Path:
        """Get the full path to the SSL key file."""
        return Path(self.directory) / self.ssl_keyfile

    @property
    def ssl_cert_file_path(self) -> Path:
        """Get the full path to the SSL certificate file."""
        return Path(self.directory) / self.ssl_certfile


class JSONResponseConfigModel(BaseModel):
    """JSON response rendering configuration model."""

    ensure_ascii: bool = Field(default=False, description="Whether to escape non-ASCII characters")
    allow_nan: bool = Field(default=False, description="Whether to allow NaN values in JSON")
    indent: int | None = Field(default=None, description="Indentation level for pretty-printing (None for compact)")
    media_type: str = Field(default="application/json; charset=utf-8", description="Media type for JSON responses")


class DatabaseConfig(BaseModel):
    """Configuration for the database."""

    db_directory: Path = Field(
        default=Path("data"), description="The directory where the SQLite database files will be stored."
    )

    def db_url(self, filename: str) -> str:
        """Construct the database URL for SQLAlchemy."""
        return f"sqlite:///{self.db_directory}/{filename}"


class TemplateServerConfig(BaseModel):
    """Template server configuration."""

    security: SecurityConfigModel = Field(default_factory=SecurityConfigModel)
    cors: CORSConfigModel = Field(default_factory=CORSConfigModel)
    rate_limit: RateLimitConfigModel = Field(default_factory=RateLimitConfigModel)
    certificate: CertificateConfigModel = Field(default_factory=CertificateConfigModel)
    json_response: JSONResponseConfigModel = Field(default_factory=JSONResponseConfigModel)

    def save_to_file(self, filepath: Path) -> None:
        """Save the configuration to a JSON file.

        :param Path filepath: Path to the configuration file
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")


# API Response Models
class CustomJSONResponse(JSONResponse):
    """Custom JSONResponse with configurable rendering options."""

    _ensure_ascii: bool = False
    _allow_nan: bool = False
    _indent: int | None = None

    @classmethod
    def configure(cls, json_response_config: JSONResponseConfigModel) -> None:
        """Configure class-level JSON rendering options."""
        cls._ensure_ascii = json_response_config.ensure_ascii
        cls._allow_nan = json_response_config.allow_nan
        cls._indent = json_response_config.indent
        cls.media_type = json_response_config.media_type

    def render(self, content: Any) -> bytes:  # noqa: ANN401
        """Render content to JSON with configured options."""
        return json.dumps(
            content,
            ensure_ascii=self._ensure_ascii,
            allow_nan=self._allow_nan,
            indent=self._indent,
            separators=(",", ":"),
        ).encode("utf-8")


class ResponseCode(IntEnum):
    """HTTP response codes for API endpoints."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class BaseResponse(BaseModel):
    """Base response model for all API endpoints."""

    message: str = Field(..., description="Human-readable message describing the response")
    timestamp: str = Field(
        default_factory=lambda: f"{datetime.now(UTC).isoformat()}Z",
        description="Timestamp of the response in ISO 8601 format",
    )

    @staticmethod
    def current_timestamp() -> str:
        """Get the current timestamp in ISO 8601 format."""
        return f"{datetime.now(UTC).isoformat()}Z"


class GetHealthResponse(BaseResponse):
    """Response model for the health endpoint."""


class GetLoginResponse(BaseResponse):
    """Response model for login endpoint."""
