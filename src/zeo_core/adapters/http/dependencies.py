
"""
FastAPI dependencies for HTTP adapter.

This module provides dependency injection functions that extract
resources from app.state for use in route handlers.
"""

from typing import cast

from fastapi import Request
from zeo_core.adapters.http.auth import require_bearer
from zeo_core.adapters.http.config import HttpAdapterConfig
from zeo_core.core.jobs import JobRunner, JobStore
from zeo_core.core.registry import OperationRegistry


def get_cfg(request: Request) -> HttpAdapterConfig:
    """
    Get HTTP adapter configuration from app state.

    Args:
        request: FastAPI request

    Returns:
        Configuration object
    """
    return cast(HttpAdapterConfig, request.app.state.cfg)


def get_registry(request: Request) -> OperationRegistry:
    """
    Get operation registry from app state.

    Args:
        request: FastAPI request

    Returns:
        Operation registry
    """
    return cast(OperationRegistry, request.app.state.registry)


def get_job_store(request: Request) -> JobStore:
    """
    Get job store from app state.

    Args:
        request: FastAPI request

    Returns:
        Job store
    """
    return cast(JobStore, request.app.state.job_store)


def get_job_runner(request: Request) -> JobRunner:
    """
    Get job runner from app state.

    Args:
        request: FastAPI request

    Returns:
        Job runner
    """
    return cast(JobRunner, request.app.state.job_runner)


def require_auth(request: Request) -> None:
    """
    Dependency that enforces authentication.

    Args:
        request: FastAPI request

    Raises:
        HTTPException: If authentication fails
    """
    cfg = get_cfg(request)
    require_bearer(request, cfg)
