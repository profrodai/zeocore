# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/_internal/context.py
# module: quack_core.core.paths._internal.context
# role: module
# neighbors: __init__.py, utils.py, resolver.py
# exports: ProjectDirectory, ProjectContext, ContentContext, PathInfo
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
DEPRECATED.

The context models have been moved to `quack_core.core.paths.models` to separate
public types from internal implementation details.

This file is a stub to prevent immediate import errors during refactoring but
should be removed in the next cleanup cycle.
"""

from quack_core.core.paths.models import (
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