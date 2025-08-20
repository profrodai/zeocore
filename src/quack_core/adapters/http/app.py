# quack-core/src/quack-core/adapters/http/app.py
"""
FastAPI application factory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import HttpAdapterConfig
from .routes import health, jobs, quackmedia
from . import jobs as jobs_module


def create_app(cfg: HttpAdapterConfig = None) -> FastAPI:
    """
    Create FastAPI application.

    Args:
        cfg: HTTP adapter configuration

    Returns:
        Configured FastAPI app
    """
    cfg = cfg or HttpAdapterConfig()

    # Initialize job system
    jobs_module.set_cfg(cfg)

    # Set config for route modules
    jobs.set_config(cfg)
    quackmedia.set_config(cfg)

    app = FastAPI(
        title="QuackCore API",
        version="0.1.0",
        description="HTTP API for QuackCore operations"
    )

    # CORS middleware
    if cfg.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
    app.include_router(quackmedia.router, prefix="/quack-media", tags=["quack-media"])

    return app