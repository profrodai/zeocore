# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/full_class.py
# === QV-LLM:END ===

from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.results import (
    BoolResult,
    DataResult,
    DirectoryInfoResult,
    FileInfoResult,
    OperationResult,
    PathResult,
)
from quack_core.core.fs.service.base import _BaseFileSystemService
from quack_core.core.fs.service.directory_operations import DirectoryOperationsMixin
from quack_core.core.fs.service.file_info_operations import FileInfoOperationsMixin
from quack_core.core.fs.service.file_operations import FileOperationsMixin
from quack_core.core.fs.service.path_operations import PathOperationsMixin
from quack_core.core.fs.service.path_validation import PathValidationMixin
from quack_core.core.fs.service.structured_data import StructuredDataMixin
from quack_core.core.fs.service.utility_operations import UtilityOperationsMixin


class FileSystemService(
    _BaseFileSystemService,
    DirectoryOperationsMixin,
    FileOperationsMixin,
    FileInfoOperationsMixin,
    StructuredDataMixin,
    PathOperationsMixin,
    PathValidationMixin,
    UtilityOperationsMixin,
):
    """
    The main, canonical FileSystem Service.
    Composed of all operation mixins with base functionality.

    This is the ONLY public FileSystemService class.
    """

    # Aliases to match ARCHITECTURE.md method catalogue
    # NOTE: These return typed Results for doctrine compliance

    def exists(self, path: FsPathLike) -> BoolResult:
        """Alias for path_exists()."""
        return self.path_exists(path)

    def resolve(self, path: FsPathLike) -> PathResult:
        """Alias for resolve_path()."""
        return self.resolve_path(path)

    def ensure_dir(self, path: FsPathLike, exist_ok: bool = True) -> OperationResult:
        """
        Alias for ensure_directory().
        Note: Always creates parent directories (parents=True internally).
        """
        return self.ensure_directory(path, exist_ok)

    def list_dir(
        self,
        path: FsPathLike,
        pattern: str | None = None,
        recursive: bool = False,
        include_hidden: bool = False,
    ) -> DirectoryInfoResult:
        """Alias for list_directory()."""
        return self.list_directory(path, pattern, recursive, include_hidden)

    def is_file(self, path: FsPathLike) -> BoolResult:
        """Check if path is a file."""
        res = self.get_file_info(path)
        return BoolResult(
            ok=res.ok,
            path=res.path,
            value=res.is_file,
            error_info=res.error_info,
            error=res.error,
            message=f"Is file: {res.is_file}" if res.ok else res.message,
        )

    def is_dir(self, path: FsPathLike) -> BoolResult:
        """Check if path is a directory."""
        res = self.get_file_info(path)
        return BoolResult(
            ok=res.ok,
            path=res.path,
            value=res.is_dir,
            error_info=res.error_info,
            error=res.error,
            message=f"Is dir: {res.is_dir}" if res.ok else res.message,
        )

    def stat(self, path: FsPathLike) -> FileInfoResult:
        """Alias for get_file_info()."""
        return self.get_file_info(path)

    def hash_file(self, path: FsPathLike, algorithm: str = "sha256") -> DataResult[str]:
        """Alias for compute_checksum()."""
        return self.compute_checksum(path, algorithm)

    def mime_type(self, path: FsPathLike) -> DataResult[str | None]:
        """Alias for get_mime_type()."""
        return self.get_mime_type(path)
