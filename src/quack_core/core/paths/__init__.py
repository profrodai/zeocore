# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/__init__.py
# module: quack_core.core.paths.__init__
# role: module
# neighbors: service.py, models.py, plugin.py
# exports: PathService, get_path_service, ProjectContext, ContentContext, ProjectDirectory, PathResult, StringResult, ContextResult
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===


"""
Path resolution and management utilities for quack_core.

This package provides utilities for resolving paths, detecting project structure,
and inferring context in QuackCore projects.

NOTE: This module does NOT expose low-level path manipulation (join/split).
Use `quack_core.core.fs` for filesystem primitives.
"""

from quack_core.core.paths.api.public.results import (
    ContextResult,
    PathResult,
    StringResult,
)
from quack_core.core.paths.models import (
    ContentContext,
    ProjectContext,
    ProjectDirectory,
)
from quack_core.core.paths.service import PathService

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
