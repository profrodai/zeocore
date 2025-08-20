# quack-core/src/quack-core/paths/api/public/__init__.py
"""
Public API for the paths module.

This package provides the public API for the paths module,
including result types for path operations.
"""

from quackcore.paths.api.public.results import ContextResult, PathResult

__all__ = [
    "PathResult",
    "ContextResult",
]
