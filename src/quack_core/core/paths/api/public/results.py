# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/api/public/results.py
# module: quack_core.core.paths.api.public.results
# role: api
# neighbors: __init__.py, path_utils.py
# exports: PathResult, StringResult, ContextResult
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Path resolution result models.

This module defines result models for path resolution operations.
"""

from pydantic import BaseModel
from quack_core.lib.paths.models import ContentContext, ProjectContext


class PathResult(BaseModel):
    """
    Result of a filesystem path resolution operation.

    Attributes:
        success: Whether the operation was successful.
        path: The resolved filesystem path (absolute), if successful.
        error: Error message, if unsuccessful.
    """

    success: bool
    path: str | None = None
    error: str | None = None


class StringResult(BaseModel):
    """
    Result of an operation returning a semantic string (e.g. module name).

    Attributes:
        success: Whether the operation was successful.
        value: The resulting string, if successful.
        error: Error message, if unsuccessful.
    """

    success: bool
    value: str | None = None
    error: str | None = None


class ContextResult(BaseModel):
    """
    Result of a context detection operation.

    Attributes:
        success: Whether the operation was successful.
        context: The detected context, if successful.
        error: Error message, if unsuccessful.
    """

    success: bool
    context: ProjectContext | ContentContext | None = None
    error: str | None = None