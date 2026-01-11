"""
DEPRECATED: Use quack_core.core.fs.service.standalone for utility functions.
"""
from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.fs.service import get_service

__all__ = ["FileSystemService", "get_service"]