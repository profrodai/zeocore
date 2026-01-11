# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/dependencies.py
# module: quack_core.adapters.http.dependencies
# role: adapters
# neighbors: __init__.py, app.py, service.py, models.py, config.py, auth.py (+1 more)
# exports: get_cfg, get_registry, get_job_store, get_job_runner, require_auth
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===



"""
FastAPI dependencies for HTTP adapter.

This module provides dependency injection functions that extract
resources from app.state for use in route handlers.
"""

from fastapi import Request
from quack_core.adapters.http.auth import require_bearer
from quack_core.adapters.http.config import HttpAdapterConfig
from quack_core.core.jobs import JobRunner, JobStore
from quack_core.core.registry import OperationRegistry


def get_cfg(request: Request) -> HttpAdapterConfig:
    """
    Get HTTP adapter configuration from app state.

    Args:
        request: FastAPI request

    Returns:
        Configuration object
    """
    return request.app.state.cfg


def get_registry(request: Request) -> OperationRegistry:
    """
    Get operation registry from app state.

    Args:
        request: FastAPI request

    Returns:
        Operation registry
    """
    return request.app.state.registry


def get_job_store(request: Request) -> JobStore:
    """
    Get job store from app state.

    Args:
        request: FastAPI request

    Returns:
        Job store
    """
    return request.app.state.job_store


def get_job_runner(request: Request) -> JobRunner:
    """
    Get job runner from app state.

    Args:
        request: FastAPI request

    Returns:
        Job runner
    """
    return request.app.state.job_runner


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
