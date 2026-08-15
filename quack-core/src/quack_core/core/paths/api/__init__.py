# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/api/__init__.py
# module: quack_core.core.paths.api.__init__
# role: api
# exports: PathResult, ContextResult
# git_branch: main
# git_commit: f0715f0c
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
