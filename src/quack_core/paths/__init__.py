# quack-core/src/quack_core/paths/__init__.py
"""
Path resolution and management utilities for quack_core.

This package provides utilities for resolving paths, detecting project structure,
and inferring context from file locations in QuackCore projects.
"""

"""
NOTE: This module intentionally does NOT expose low-level path functions.
Use `quack_core.fs` for join_path, split_path, etc. to avoid API duplication.
"""

from quack_core.paths._internal.context import (
    ContentContext,
    ProjectContext,
    ProjectDirectory,
)
from quack_core.paths._internal.resolver import PathResolver
from quack_core.paths._internal.utils import (
    _find_nearest_directory,
    _find_project_root,
    _infer_module_from_path,
    _normalize_path,
    _resolve_relative_to_project,
)
from quack_core.paths.service import PathService

# Create a global instance for convenience
resolver = PathResolver()
service = PathService()

__all__ = [
    # Classes
    "PathResolver",
    "PathService",
    "ProjectContext",
    "ContentContext",
    "ProjectDirectory",
    # Global instances
    "resolver",
    "service",
]
