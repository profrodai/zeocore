# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/api/public/__init__.py
# module: quack_core.core.paths.api.public.__init__
# role: api
# neighbors: results.py, path_utils.py
# exports: PathResult, ContextResult
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/paths/api/public/__init__.py
"""
Public API for the paths module.

This package provides the public API for the paths module,
including result types for path operations.
"""

from quack_core.paths.api.public.results import ContextResult, PathResult

__all__ = [
    "PathResult",
    "ContextResult",
]
