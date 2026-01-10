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