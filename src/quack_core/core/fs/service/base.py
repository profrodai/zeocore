# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/base.py
# module: quack_core.core.fs.service.base
# role: service
# neighbors: __init__.py, directory_operations.py, factory.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: FileSystemService
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

from pathlib import Path
from typing import Any
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

    def __init__(self, base_dir: str | Path | None = None, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)

        # Ensure base_dir is absolute and resolved immediately
        if base_dir:
            self.base_dir = Path(base_dir).resolve()
        else:
            self.base_dir = Path.cwd().resolve()

        # _ops layer receives resolved base_dir
        self.operations = FileSystemOperations(self.base_dir)

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        """
        SSOT for service input normalization.
        Coerces input to Path AND anchors it to the service's base_dir with sandboxing.
        """
        try:
            return coerce_path(path, base_dir=self.base_dir)
        except (TypeError, ValueError) as e:
            raise QuackValidationError(f"Invalid path input: {path}", original_error=e) from e

    def _map_error(self, e: Exception) -> ErrorInfo:
        """
        Centralized error mapping logic.
        Converts native exceptions to structured ErrorInfo.
        """
        err_type = type(e).__name__
        exception_cls = e.__class__.__name__
        msg = str(e)
        hint = None
        details = {}
        trace_id = str(uuid.uuid4())

        if isinstance(e, FileNotFoundError):
            hint = "Check if the file path is correct relative to base_dir."
        elif isinstance(e, PermissionError):
            hint = "Check file permissions or run with elevated privileges."
        elif isinstance(e, IsADirectoryError):
            hint = "Expected a file but found a directory."

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