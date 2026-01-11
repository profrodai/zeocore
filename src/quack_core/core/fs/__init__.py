"""
Filesystem package for quack_core.
"""
from quack_core.core.fs.service import FileSystemService, get_service, create_service
from quack_core.core.fs.results import (
    OperationResult, ReadResult, WriteResult, FileInfoResult,
    DirectoryInfoResult, FindResult, DataResult, PathResult, BoolResult
)

__all__ = [
    "FileSystemService", "get_service", "create_service",
    "OperationResult", "ReadResult", "WriteResult", "FileInfoResult",
    "DirectoryInfoResult", "FindResult", "DataResult", "PathResult", "BoolResult"
]