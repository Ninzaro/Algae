"""CLI entrypoint for local development."""

import uvicorn

from alphaforge.core.config import get_settings


def main() -> None:
    """Start the API with uvicorn using environment settings."""
    settings = get_settings()
    uvicorn.run(
        "alphaforge.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
