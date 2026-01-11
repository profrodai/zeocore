# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/full_class.py
# module: quack_core.core.fs.service.full_class
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, path_operations.py (+4 more)
# exports: FileSystemService
# git_branch: feat/9-make-setup-work
# git_commit: f85cce5a
# === QV-LLM:END ===

from typing import Any
from quack_core.core.fs.service.base import FileSystemService as BaseFileSystemService
from quack_core.core.fs.service.directory_operations import DirectoryOperationsMixin
from quack_core.core.fs.service.file_operations import FileOperationsMixin
from quack_core.core.fs.service.path_operations import PathOperationsMixin
from quack_core.core.fs.service.utility_operations import UtilityOperationsMixin
from quack_core.core.fs.service.structured_data import StructuredDataMixin
from quack_core.core.fs.service.path_validation import PathValidationMixin
from quack_core.core.fs.results import DataResult, PathResult, BoolResult


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
    The main Filesystem Service composed of all mixins.
    Provides canonical aliases for API completeness.
    """

    # Aliases to match ARCHITECTURE.md method catalogue
    def exists(self, path) -> BoolResult:
        return self.path_exists(path)

    def resolve(self, path) -> PathResult:
        return self.resolve_path(path)

    def ensure_dir(self, path, exist_ok=True) -> Any:
        return self.ensure_directory(path, exist_ok)

    def list_dir(self, path, pattern=None, recursive=False, include_hidden=False) -> Any:
        return self.list_directory(path, pattern, recursive, include_hidden)

    def is_file(self, path) -> BoolResult:
        """Check if path is a file."""
        res = self.get_file_info(path)
        return BoolResult(
            ok=res.ok,
            path=res.path,
            value=res.is_file,
            error_info=res.error_info,
            error=res.error,
            message=f"Is file: {res.is_file}" if res.ok else res.message
        )

    def is_dir(self, path) -> BoolResult:
        """Check if path is a directory."""
        res = self.get_file_info(path)
        return BoolResult(
            ok=res.ok,
            path=res.path,
            value=res.is_dir,
            error_info=res.error_info,
            error=res.error,
            message=f"Is dir: {res.is_dir}" if res.ok else res.message
        )