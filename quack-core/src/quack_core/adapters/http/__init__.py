# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/__init__.py
# === QV-LLM:END ===

"""
HTTP Adapter for quack_core.

Optional FastAPI-based HTTP API that exposes QuackCore _ops
via REST endpoints. Only available when the 'http' extra is installed.
"""

from typing import Any

try:
    from .app import create_app
    from .config import HttpAdapterConfig
    from .service import run

    __all__ = ["create_app", "HttpAdapterConfig", "run"]
except ImportError:
    # FastAPI not available - this is expected when http extra not installed
    def create_app(*args: Any, **kwargs: Any) -> None:
        raise ImportError(
            "HTTP adapter requires FastAPI. Install with: pip install quack-core[http]"
        )

    def run(*args: Any, **kwargs: Any) -> None:
        raise ImportError(
            "HTTP adapter requires FastAPI. Install with: pip install quack-core[http]"
        )

    class HttpAdapterConfig:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "HTTP adapter requires FastAPI. Install with: "
                "pip install quack-core[http]"
            )

    __all__ = ["create_app", "HttpAdapterConfig", "run"]
