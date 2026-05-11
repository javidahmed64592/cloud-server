"""Routers for the FastAPI server."""

from .base_router import BaseRouter
from .template_server_router import TemplateServerRouter

__all__ = ["BaseRouter", "TemplateServerRouter"]
