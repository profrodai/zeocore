# quack-core/src/quack-core/adapters/http/service.py
"""
Service utilities for running the HTTP adapter.
"""

import uvicorn
from .config import HttpAdapterConfig
from .app import create_app


def run(cfg: HttpAdapterConfig) -> None:
    """
    Run the HTTP adapter with uvicorn.

    Args:
        cfg: HTTP adapter configuration
    """
    app = create_app(cfg)

    uvicorn.run(
        app,
        host=cfg.host,
        port=cfg.port,
        log_level="info"
    )