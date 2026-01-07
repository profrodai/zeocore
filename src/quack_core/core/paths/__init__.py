
"""
Path resolution and management utilities for quack_core.

This package provides utilities for resolving paths, detecting project structure,
and inferring context in QuackCore projects.

NOTE: This module does NOT expose low-level path manipulation (join/split).
Use `quack_core.lib.fs` for filesystem primitives.
"""

from quack_core.lib.paths.api.public.results import (
    ContextResult,
    PathResult,
    StringResult,
)
from quack_core.lib.paths.models import (
    ContentContext,
    ProjectContext,
    ProjectDirectory,
)
from quack_core.lib.paths.service import PathService

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
