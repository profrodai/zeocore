# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/__init__.py
# module: quack_core.core.fs.__init__
# role: module
# neighbors: protocols.py, plugin.py, results.py
# exports: FileSystemService, get_service, create_service, OperationResult, ReadResult, WriteResult, FileInfoResult, DirectoryInfoResult (+3 more)
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

"""
Filesystem package for quack_core.
"""
from quack_core.core.fs.service import FileSystemService, get_service, create_service
from quack_core.core.fs.results import *

# For backward compatibility, allow access to api.public via main package
from quack_core.core.fs.api.public import *

__all__ = [
    "FileSystemService", "get_service", "create_service",
    "OperationResult", "ReadResult", "WriteResult", "FileInfoResult",
    "DirectoryInfoResult", "FindResult", "DataResult", "PathResult"
]