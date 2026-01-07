# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/full_class.py
# module: quack_core.core.fs.service.full_class
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, path_operations.py (+4 more)
# exports: FileSystemService
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/service/full_class.py
"""
Combined FileSystemService class definition that incorporates all mixins.

This module re-exports the complete FileSystemService to provide backward compatibility
with existing code.
"""

from quack_core.fs.service.base import FileSystemService as BaseFileSystemService
from quack_core.fs.service.directory_operations import DirectoryOperationsMixin
from quack_core.fs.service.file_operations import FileOperationsMixin
from quack_core.fs.service.path_operations import PathOperationsMixin
from quack_core.fs.service.path_validation import PathValidationMixin
from quack_core.fs.service.structured_data import StructuredDataMixin
from quack_core.fs.service.utility_operations import UtilityOperationsMixin


class FileSystemService(
    BaseFileSystemService,
    FileOperationsMixin,
    DirectoryOperationsMixin,
    StructuredDataMixin,
    PathOperationsMixin,
    PathValidationMixin,
    UtilityOperationsMixin,
):
    """
    High-level service for filesystem _operations.

    This service provides a clean, consistent API for all file _operations
    in QuackCore, with proper error handling and result objects.
    """

    # All functionality is inherited from the mixins
    pass
