# quack-core/src/quack-core/paths/api/public/results.py
"""
Path resolution result models.

This module defines result models for path resolution operations.
"""


from pydantic import BaseModel

from quackcore.paths._internal.context import ContentContext, ProjectContext


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
