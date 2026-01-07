# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/service.py
# module: quack_core.adapters.http.service
# role: service
# neighbors: __init__.py, app.py, models.py, config.py, auth.py, dependencies.py (+1 more)
# exports: run
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

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

    uvicorn.run(
        app,
        host=cfg.host,
        port=cfg.port,
        log_level="info"
    )
