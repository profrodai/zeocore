# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/__init__.py
# module: quack_core.core.fs.api.public.__init__
# role: api
# exports: FileSystemService, get_service
# git_branch: feat/9-make-setup-work
# git_commit: 2d6aea0e
# === QV-LLM:END ===

"""
DEPRECATED: Use quack_core.core.fs.service.standalone for utility functions.
"""
from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.fs.service import get_service

__all__ = ["FileSystemService", "get_service"]