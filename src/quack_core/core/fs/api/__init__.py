"""
DEPRECATED: Use quack_core.core.fs.service.standalone for utility functions.
"""
import warnings
from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.fs.service import get_service

__all__ = ["FileSystemService", "get_service"]

warnings.warn("quack_core.core.fs.api is deprecated. Use quack_core.core.fs.service.standalone or get_service() instead.", DeprecationWarning, stacklevel=2)