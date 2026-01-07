"""
Public API for the paths module.

This package provides the public API for the paths module,
including result types for path operations.
"""

from quack_core.lib.paths.api.public.results import ContextResult, PathResult

__all__ = [
    "PathResult",
    "ContextResult",
]