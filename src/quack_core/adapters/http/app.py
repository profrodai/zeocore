# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/app.py
# module: quack_core.adapters.http.app
# role: adapters
# neighbors: __init__.py, service.py, models.py, config.py, auth.py, dependencies.py (+1 more)
# exports: create_app
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===



"""
FastAPI application factory with dependency injection.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from quack_core.adapters.http.config import HttpAdapterConfig
from quack_core.adapters.http.routes import health, jobs, operations
from quack_core.core.jobs import InMemoryJobStore, JobStore, ThreadPoolJobRunner
from quack_core.core.logging import get_logger
from quack_core.core.registry import OperationRegistry, get_registry

logger = get_logger(__name__)


async def cleanup_task(store: JobStore, ttl_seconds: int) -> None:
    """Background task to cleanup expired jobs."""
    while True:
        try:
            await asyncio.sleep(300)  # Cleanup every 5 minutes
            count = store.cleanup_expired(ttl_seconds)
            if count > 0:
                logger.info(f"Background cleanup removed {count} expired jobs")
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup/shutdown.

    Handles initialization and cleanup of resources like job runners.
    Skips initialization if dependencies already injected (for testing).
    """
    logger.info("Starting HTTP adapter")

    # Check if dependencies already injected (test mode)
    if not hasattr(app.state, "registry"):
        # Initialize job system
        cfg: HttpAdapterConfig = app.state.cfg
        registry = get_registry()
        store = InMemoryJobStore()
        runner = ThreadPoolJobRunner(
            registry=registry,
            store=store,
            max_workers=cfg.max_workers,
            hmac_secret=cfg.hmac_secret,
        )

        # Store in app state
        app.state.job_store = store
        app.state.job_runner = runner
        app.state.registry = registry

        # Start background cleanup task
        cleanup = asyncio.create_task(cleanup_task(store, cfg.job_ttl_seconds))
        app.state.cleanup_task = cleanup

        logger.info("Job system initialized")
    else:
        logger.info("Job system pre-injected (test mode)")
        cleanup = None

    yield

    # Cleanup
    logger.info("Shutting down HTTP adapter")
    if cleanup is not None:
        cleanup.cancel()
        try:
            await cleanup
        except asyncio.CancelledError:
            pass

    if hasattr(app.state, "job_runner"):
        app.state.job_runner.shutdown(wait=True)

    logger.info("HTTP adapter stopped")


def create_app(
        cfg: HttpAdapterConfig | None = None,
        registry: OperationRegistry | None = None,
        job_store: InMemoryJobStore | None = None,
        job_runner: ThreadPoolJobRunner | None = None,
) -> FastAPI:
    """
    Create FastAPI application with dependency injection.

    Args:
        cfg: HTTP adapter configuration
        registry: Optional registry override (for testing)
        job_store: Optional job store override (for testing)
        job_runner: Optional job runner override (for testing)

    Returns:
        Configured FastAPI app with all dependencies in app.state
    """
    cfg = cfg or HttpAdapterConfig()

    app = FastAPI(
        title="QuackCore API",
        version="0.1.0",
        description="HTTP API for QuackCore _ops",
        lifespan=lifespan,
    )

    # Store config in app state (dependency injection source)
    app.state.cfg = cfg

    # Allow test overrides (bypasses lifespan initialization)
    if registry is not None:
        app.state.registry = registry
    if job_store is not None:
        app.state.job_store = job_store
    if job_runner is not None:
        app.state.job_runner = job_runner

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
    app.include_router(operations.router, prefix="/ops", tags=["_ops"])

    logger.info("FastAPI app created")

    return app
