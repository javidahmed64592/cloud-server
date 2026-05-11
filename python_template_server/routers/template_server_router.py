"""Template server router with health and login endpoints."""

from fastapi import Request

from python_template_server.models import GetHealthResponse, GetLoginResponse
from python_template_server.routers import BaseRouter


class TemplateServerRouter(BaseRouter):
    """Router for the template server with health and login endpoints."""

    def setup_routes(self) -> None:
        """Set up the API routes for the template server."""
        self.add_route(
            endpoint="/health",
            handler_function=self.get_health,
            response_model=GetHealthResponse,
            methods=["GET"],
            limited=False,
            authentication_required=False,
        )
        self.add_route(
            endpoint="/login",
            handler_function=self.get_login,
            response_model=GetLoginResponse,
            methods=["GET"],
            limited=True,
            authentication_required=True,
        )

    async def get_health(self, request: Request) -> GetHealthResponse:
        """Get server health.

        :param Request request: The incoming HTTP request
        :return GetHealthResponse: Health status response
        :raise HTTPException: If the server token is not configured
        """
        return GetHealthResponse(message="Server is healthy")

    async def get_login(self, request: Request) -> GetLoginResponse:
        """Handle user login and return a success response.

        :param Request request: The incoming HTTP request
        :return GetLoginResponse: Login success response
        :raise HTTPException: If the server token is not configured
        """
        return GetLoginResponse(message="Login successful.")
