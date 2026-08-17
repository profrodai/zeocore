"""
HTTP Adapter for zeo_core.

Optional FastAPI-based HTTP API that exposes ZeoCore _ops
via REST endpoints. Only available when the 'http' extra is installed.
"""

from typing import Any

try:
    from .app import create_app
    from .config import HttpAdapterConfig
    from .service import run

    __all__ = ["create_app", "HttpAdapterConfig", "run"]
except ImportError:
    # FastAPI not available - this is expected when http extra not installed.
    # These stubs deliberately do not (and cannot) mirror the real create_app/
    # run/HttpAdapterConfig signatures -- the real ones live in the modules
    # that just failed to import, so their types are unavailable here. Each
    # stub's only job is to raise a clear, actionable ImportError the moment
    # it is used, never to be call-compatible with the real implementation.
    # mypy strict (correctly, given only this file's own two branches) flags
    # the signature mismatch [misc] and the name redefinition [no-redef];
    # both are inherent to this fallback-shim shape, not a fixable type gap.
    def create_app(  # type: ignore[misc]
        *args: Any,  # noqa: ANN401 -- genuinely dynamic: stub shim mirrors the real create_app's arbitrary signature, only ever raises
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
    ) -> None:
        raise ImportError(
            "HTTP adapter requires FastAPI. Install with: pip install zeocore[http]"
        )

    def run(  # type: ignore[misc]
        *args: Any,  # noqa: ANN401 -- genuinely dynamic: stub shim mirrors the real run's arbitrary signature, only ever raises
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
    ) -> None:
        raise ImportError(
            "HTTP adapter requires FastAPI. Install with: pip install zeocore[http]"
        )

    class HttpAdapterConfig:  # type: ignore[no-redef]
        def __init__(
            self,
            *args: Any,  # noqa: ANN401 -- genuinely dynamic: stub shim mirrors the real HttpAdapterConfig's arbitrary signature, only ever raises
            **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
        ) -> None:
            raise ImportError(
                "HTTP adapter requires FastAPI. Install with: "
                "pip install zeocore[http]"
            )

    __all__ = ["create_app", "HttpAdapterConfig", "run"]
