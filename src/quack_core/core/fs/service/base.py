# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/base.py
# module: quack_core.core.fs.service.base
# role: service
# neighbors: __init__.py, directory_operations.py, factory.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: FileSystemService
# git_branch: feat/9-make-setup-work
# git_commit: 10c11a25
# === QV-LLM:END ===

from pathlib import Path
from typing import Any, Optional
import uuid

from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.normalize import coerce_path
from quack_core.core.fs.results import ErrorInfo
from quack_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from quack_core.core.errors import QuackValidationError


class FileSystemService:
    """
    Central FileSystem Service.
    Handles configuration, normalization (anchored), and error mapping.
    """

    def __init__(self, base_dir: str | Path | None = None, log_level: int = LOG_LEVELS[LogLevel.INFO],
                 allow_absolute_paths: bool = False) -> None:
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)
        self.allow_absolute_paths = allow_absolute_paths

        # Ensure base_dir is absolute and resolved immediately
        if base_dir:
            self.base_dir = Path(base_dir).resolve()
        else:
            self.base_dir = Path.cwd().resolve()

        self.operations = FileSystemOperations()

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        """
        SSOT for service input normalization.
        Coerces input to Path AND anchors it to the service's base_dir with sandboxing.
        """
        try:
            return coerce_path(path, base_dir=self.base_dir, allow_absolute=self.allow_absolute_paths)
        except (TypeError, ValueError) as e:
            raise QuackValidationError(f"Invalid path input: {path}", original_error=e) from e

    def _map_error(self, e: Exception) -> ErrorInfo:
        """
        Centralized error mapping logic.
        Converts native exceptions to structured ErrorInfo with stable IDs.
        """
        exception_cls = e.__class__.__name__
        msg = str(e)
        hint = None
        details = {}
        trace_id = str(uuid.uuid4())

        # Stable snake_case IDs
        err_type = "unknown_error"

        if isinstance(e, FileNotFoundError):
            err_type = "file_not_found"
            hint = "Check if the file path is correct relative to base_dir."
        elif isinstance(e, PermissionError):
            err_type = "permission_denied"
            hint = "Check file permissions or run with elevated privileges."
        elif isinstance(e, IsADirectoryError):
            err_type = "is_a_directory"
            hint = "Expected a file but found a directory."
        elif isinstance(e, NotADirectoryError):
            err_type = "not_a_directory"
            hint = "Expected a directory but found a file."
        elif isinstance(e, OSError):
            err_type = "io_error"
        elif isinstance(e, ValueError):  # Catch sandbox violations
            err_type = "validation_error"

        if hasattr(e, 'filename'):
            details['filename'] = str(e.filename)
        if hasattr(e, 'errno'):
            details['errno'] = e.errno

        return ErrorInfo(
            type=err_type,
            message=msg,
            hint=hint,
            exception=exception_cls,
            trace_id=trace_id,
            details=details
        )