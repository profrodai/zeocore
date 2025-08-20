# quack-core/src/quack-core/fs/service/full_class.py
"""
Combined FileSystemService class definition that incorporates all mixins.

This module re-exports the complete FileSystemService to provide backward compatibility
with existing code.
"""

from quackcore.fs.service.base import FileSystemService as BaseFileSystemService
from quackcore.fs.service.directory_operations import DirectoryOperationsMixin
from quackcore.fs.service.file_operations import FileOperationsMixin
from quackcore.fs.service.path_operations import PathOperationsMixin
from quackcore.fs.service.path_validation import PathValidationMixin
from quackcore.fs.service.structured_data import StructuredDataMixin
from quackcore.fs.service.utility_operations import UtilityOperationsMixin


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
