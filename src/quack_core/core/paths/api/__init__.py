# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/api/__init__.py
# module: quack_core.core.paths.api.__init__
# role: api
# exports: PathResult, ContextResult
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

"""
API package for the paths module.

This package provides the API for the paths module,
including both public and internal interfaces.
"""

from quack_core.core.paths.api.public import ContextResult, PathResult

__all__ = [
    "PathResult",
    "ContextResult",
]