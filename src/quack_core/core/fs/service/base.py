# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/base.py
# module: quack_core.core.fs.service.base
# role: service
# neighbors: __init__.py, directory_operations.py, factory.py, file_info_operations.py, file_operations.py, full_class.py (+5 more)
# git_branch: main
# git_commit: f0715f0c
# === QV-LLM:END ===


import uuid
from pathlib import Path

from quack_core.core.errors import QuackValidationError
from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.exceptions import (
    QuackPathEscapeError,
    QuackPathOutsideBaseDirError,
)
from quack_core.core.fs.normalize import coerce_path
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.results import ErrorInfo
from quack_core.core.logging import LOG_LEVELS, LogLevel, get_logger


class _BaseFileSystemService:
    """
    Base FileSystem Service class (internal).
    Handles configuration, normalization (anchored), and error mapping.

    NOTE: This is an internal base class. The public class is FileSystemService
    in service/full_class.py.
    """

    def __init__(self, base_dir: str | Path | None = None, log_level: int = LOG_LEVELS[LogLevel.INFO],
                 unsafe_allow_absolute_paths: bool = False) -> None:
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)
        self.unsafe_allow_absolute_paths = unsafe_allow_absolute_paths

        # Ensure base_dir is absolute and resolved immediately
        if base_dir:
            self.base_dir = Path(base_dir).resolve()
        else:
            self.base_dir = Path.cwd().resolve()

        # SECURITY: Warn if sandboxing is disabled
        # This is a trust boundary configuration, not a convenience feature
        if self.unsafe_allow_absolute_paths:
            self.logger.warning(
                "⚠️  SECURITY WARNING: unsafe_allow_absolute_paths=True - "
                "Absolute paths outside base_dir are permitted. Operations can access paths "
                "outside the sandbox root. Relative-path escape via '..' remains BLOCKED "
                "(this flag does not disable the '..' traversal check). "
                "NOTE: This does NOT protect against symlink-based TOCTOU attacks or symlinks "
                "inside base_dir that point outside. For maximum security, use a dedicated "
                "filesystem namespace or container-level isolation. "
                "Only enable this in fully trusted environments."
            )

        self.operations = FileSystemOperations()

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        """
        SSOT for service input normalization.
        Coerces input to Path AND anchors it to the service's base_dir with sandboxing.
        """
        try:
            return coerce_path(path, base_dir=self.base_dir, allow_absolute=self.unsafe_allow_absolute_paths)
        except (QuackPathEscapeError, QuackPathOutsideBaseDirError) as e:
            # Re-raise sandbox violations to be mapped to specific error types
            raise e
        except ValueError as e:
            # Wrap standard coercion errors in QuackValidationError
            raise QuackValidationError(f"Invalid path input: {path}", original_error=e) from e
        except TypeError as e:
            # Wrap shape/type errors
            raise QuackValidationError(f"Invalid path input type: {path}", original_error=e) from e
        except Exception as e:
            raise QuackValidationError(f"Invalid path input: {path}", original_error=e) from e

    def _map_error(self, e: Exception) -> ErrorInfo:
        """
        Centralized error mapping logic.
        Converts native exceptions to structured ErrorInfo with stable IDs.

        CRITICAL: Order matters - most specific exceptions first!
        """
        exception_cls = e.__class__.__name__
        msg = str(e)
        hint = None
        details = {}
        trace_id = str(uuid.uuid4())

        # Stable snake_case IDs
        err_type = "unknown_error"

        # SECURITY ERRORS FIRST (most specific)
        if isinstance(e, QuackPathEscapeError):
            err_type = "path_escape_attempt"
            hint = "Path attempted to traverse above the base directory using '..' or similar."
        elif isinstance(e, QuackPathOutsideBaseDirError):
            err_type = "path_outside_base_dir"
            hint = "Absolute paths outside the configured base directory are not allowed (unsafe_allow_absolute_paths=False)."

        # VALIDATION ERRORS
        elif isinstance(e, QuackValidationError):
            err_type = "validation_error"
            hint = "The input path is invalid, malformed, or unsafe."
        elif isinstance(e, TypeError):
            err_type = "validation_error"
            hint = "Invalid path input type or shape."

        # FILE SYSTEM ERRORS (specific before general)
        elif isinstance(e, FileNotFoundError):
            err_type = "file_not_found"
            hint = "Check if the file path is correct relative to base_dir."
        elif isinstance(e, FileExistsError):
            err_type = "file_exists"
            hint = "Target already exists. Use overwrite=True or choose a different path."
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
            hint = "An operating system error occurred during filesystem access."

        # VALUE ERRORS (generic bucket, after specific checks)
        elif isinstance(e, ValueError):
            msg_lower = msg.lower()
            if "unsupported algorithm" in msg_lower:
                err_type = "unsupported_algorithm"
                hint = "Check the requested hash algorithm."
            elif "invalid regex" in msg_lower:
                err_type = "invalid_regex"
                hint = "The provided regular expression pattern is invalid."
            elif "is not a dict" in msg_lower:  # Catching yaml/json parsing errors from ops
                err_type = "invalid_data_format"
                hint = "The file content structure does not match the expected format (e.g. dict)."
            else:
                err_type = "validation_error"
                hint = "Input validation failed."

        # Extract error details if available
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
            details=details if details else None
        )
