"""
DEPRECATED.

The context models have been moved to `quack_core.lib.paths.models` to separate
public types from internal implementation details.

This file is a stub to prevent immediate import errors during refactoring but
should be removed in the next cleanup cycle.
"""

from quack_core.lib.paths.models import (
    ContentContext,
    PathInfo,
    ProjectContext,
    ProjectDirectory,
)

__all__ = [
    "ProjectDirectory",
    "ProjectContext",
    "ContentContext",
    "PathInfo",
]