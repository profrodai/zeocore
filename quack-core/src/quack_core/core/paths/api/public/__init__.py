# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/api/public/__init__.py
# === QV-LLM:END ===

"""
Public API for the paths module.

This package provides the public API for the paths module,
including result types for path _ops.
"""

from quack_core.core.paths.api.public.results import ContextResult, PathResult

__all__ = [
    "PathResult",
    "ContextResult",
]
