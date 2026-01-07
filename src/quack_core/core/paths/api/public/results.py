# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/api/public/results.py
# module: quack_core.core.paths.api.public.results
# role: api
# neighbors: __init__.py, path_utils.py
# exports: PathResult, ContextResult
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/paths/api/public/results.py
"""
Path resolution result models.

This module defines result models for path resolution operations.
"""


from pydantic import BaseModel

from quack_core.paths._internal.context import ContentContext, ProjectContext


class PathResult(BaseModel):
    """
    Result of a path resolution operation.

    Attributes:
        success: Whether the operation was successful.
        path: The resolved path, if successful.
        error: Error message, if unsuccessful.
    """

    success: bool
    path: str | None = None
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
