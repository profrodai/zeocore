# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/full_class.py
# module: quack_core.core.fs.service.full_class
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, path_operations.py (+4 more)
# exports: FileSystemService
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from quack_core.core.fs.service.base import FileSystemService as BaseFileSystemService
from quack_core.core.fs.service.directory_operations import DirectoryOperationsMixin
from quack_core.core.fs.service.file_operations import FileOperationsMixin
from quack_core.core.fs.service.path_operations import PathOperationsMixin
from quack_core.core.fs.service.utility_operations import UtilityOperationsMixin
from quack_core.core.fs.service.structured_data import StructuredDataMixin
from quack_core.core.fs.service.path_validation import PathValidationMixin

class FileSystemService(
    BaseFileSystemService,
    FileOperationsMixin,
    DirectoryOperationsMixin,
    StructuredDataMixin,
    PathOperationsMixin,
    PathValidationMixin,
    UtilityOperationsMixin,
):
    pass