"""
Path resolution and management utilities for zeo_core.

This package provides utilities for resolving paths, detecting project structure,
and inferring context in ZeoCore projects.

NOTE: This module does NOT expose low-level path manipulation (join/split).
Use `zeo_core.core.fs` for filesystem primitives.
"""

from zeo_core.core.paths._internal.resolver import PathResolver
from zeo_core.core.paths.api.public.results import (
    ContextResult,
    PathResult,
    StringResult,
)
from zeo_core.core.paths.models import (
    ContentContext,
    ProjectContext,
    ProjectDirectory,
)
from zeo_core.core.paths.service import PathService

# Lazy singleton
_service: PathService | None = None


def get_path_service() -> PathService:
    """Get the global PathService instance."""
    global _service
    if _service is None:
        _service = PathService()
    return _service


__all__ = [
    # Service Access
    "PathService",
    "PathResolver",
    "get_path_service",
    # Models
    "ProjectContext",
    "ContentContext",
    "ProjectDirectory",
    # Results
    "PathResult",
    "StringResult",
    "ContextResult",
]
