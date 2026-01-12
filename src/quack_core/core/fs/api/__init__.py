# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/__init__.py
# module: quack_core.core.fs.api.__init__
# role: api
# exports: FileSystemService, get_service
# git_branch: feat/9-make-setup-work
# git_commit: 2d6aea0e
# === QV-LLM:END ===

"""
DEPRECATED: Use quack_core.core.fs.service.standalone for utility functions.
"""
import warnings
from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.fs.service import get_service

__all__ = ["FileSystemService", "get_service"]

warnings.warn("quack_core.core.fs.api is deprecated. Use quack_core.core.fs.service.standalone or get_service() instead.", DeprecationWarning, stacklevel=2)