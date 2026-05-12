"""FastAPI-based local cloud server using uvicorn."""

from cloud_server.server import CloudServer


def run() -> None:
    """Serve the FastAPI application using uvicorn."""
    server = CloudServer()
    server.run()
