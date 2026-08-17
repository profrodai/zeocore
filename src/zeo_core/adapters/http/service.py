"""
Service utilities for running the HTTP adapter.
"""

import uvicorn

from .app import create_app
from .config import HttpAdapterConfig


def run(cfg: HttpAdapterConfig) -> None:
    """
    Run the HTTP adapter with uvicorn.

    Args:
        cfg: HTTP adapter configuration
    """
    app = create_app(cfg)

    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")
