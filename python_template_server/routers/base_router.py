"""Base router for the FastAPI server."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from slowapi import Limiter

from python_template_server.authentication_handler import verify_token
from python_template_server.constants import API_KEY_HEADER_NAME
from python_template_server.models import ResponseCode

logger = logging.getLogger(__name__)


API_KEY_HEADER = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


class BaseRouter(ABC):
    """Abstract base class for API routers."""

    def __init__(self, prefix: str) -> None:
        """Initialize the base router."""
        logger.info("Initializing router with prefix: %s", prefix or "/")
        self.router = APIRouter(prefix=prefix)

        self.hashed_token: str = ""
        self.limiter: Limiter | None
        self.rate_limit: str

    @abstractmethod
    def setup_routes(self) -> None:
        """Abstract method to set up API routes."""
        pass

    async def _verify_api_key(self, api_key: str | None = Security(API_KEY_HEADER)) -> None:
        """Verify the API key from the request header.

        :param str | None api_key: The API key from the X-API-Key header
        :raise HTTPException: If the API key is missing or invalid
        """
        if api_key is None:
            logger.warning("Missing API key in request!")
            raise HTTPException(
                status_code=ResponseCode.BAD_REQUEST,
                detail="Missing API key",
            )

        try:
            if not verify_token(api_key, self.hashed_token):
                logger.warning("Invalid API key attempt!")
                raise HTTPException(
                    status_code=ResponseCode.UNAUTHORIZED,
                    detail="Invalid API key",
                )
        except ValueError as e:
            logger.exception("Error verifying API key!")
            raise HTTPException(
                status_code=ResponseCode.INTERNAL_SERVER_ERROR,
                detail=str(e),
            ) from e

    def configure(self, hashed_token: str, limiter: Limiter | None, rate_limit: str) -> None:
        """Configure the router with shared dependencies.

        :param str hashed_token: The hashed token for API key verification
        :param Limiter | None limiter: The rate limiter instance to use for this router
        :param str rate_limit: The rate limit string to apply to limited routes
        """
        self.hashed_token = hashed_token
        self.limiter = limiter
        self.rate_limit = rate_limit

    def add_route(
        self,
        endpoint: str,
        handler_function: Callable,
        response_model: type[BaseModel],
        methods: list[str],
        limited: bool,  # noqa: FBT001
        authentication_required: bool,  # noqa: FBT001
    ) -> None:
        """Add an API route.

        :param str endpoint: The API endpoint path
        :param Callable handler_function: The handler function for the endpoint
        :param BaseModel response_model: The Pydantic model for the response
        :param list[str] methods: The HTTP methods for the endpoint
        :param bool limited: Whether to apply rate limiting to this route
        :param bool authentication_required: Whether authentication is required for this route
        """
        try:
            limited_method = None
            if limited and self.limiter is not None:
                limited_method = self.limiter.limit(self.rate_limit)(handler_function)

            self.router.add_api_route(
                path=endpoint,
                endpoint=limited_method or handler_function,
                methods=methods,
                response_model=response_model,
                dependencies=[Security(self._verify_api_key)] if authentication_required else None,
            )
        except AttributeError as e:
            error_msg = "Router not configured with limiter and rate limit. Call configure() before adding routes."
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
