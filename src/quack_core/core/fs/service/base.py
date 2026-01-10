from pathlib import Path
from typing import Any

from quack_core.fs.operations.base import FileSystemOperations
from quack_core.fs.protocols import FsPathLike
from quack_core.fs.normalize import coerce_path
from quack_core.fs.results import ErrorInfo
from quack_core.lib.logging import LOG_LEVELS, LogLevel, get_logger
from quack_core.lib.errors import QuackValidationError


class FileSystemService:
    """
    Central FileSystem Service.
    Handles configuration, normalization, and error mapping.
    """

    def __init__(self, base_dir: str | Path | None = None, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.operations = FileSystemOperations(self.base_dir)

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        """
        SSOT for service input normalization.
        Uses fs.normalize to coerce inputs.
        """
        try:
            return coerce_path(path)
        except (TypeError, ValueError) as e:
            raise QuackValidationError(f"Invalid path input: {path}", original_error=e) from e

    def _map_error(self, e: Exception) -> ErrorInfo:
        """
        Centralized error mapping logic.
        Converts native exceptions to structured ErrorInfo.
        """
        err_type = type(e).__name__
        msg = str(e)
        hint = None

        if isinstance(e, FileNotFoundError):
            err_type = "FileNotFoundError"
            msg = "File or directory not found"
        elif isinstance(e, PermissionError):
            err_type = "PermissionError"
            msg = "Permission denied"
            hint = "Check file permissions or run with elevated privileges."
        elif isinstance(e, IsADirectoryError):
            err_type = "IsADirectoryError"
            msg = "Expected a file but found a directory"

        return ErrorInfo(
            type=err_type,
            message=msg,
            hint=hint,
            exception=str(e)
        )