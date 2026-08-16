# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/base.py
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

    def __init__(
        self,
        base_dir: str | Path | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        unsafe_allow_absolute_paths: bool = False,
    ) -> None:
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
                "Absolute paths outside base_dir are permitted. Operations can "
                "access paths outside the sandbox root. Relative-path escape via "
                "'..' remains BLOCKED (this flag does not disable the '..' "
                "traversal check). NOTE: This does NOT protect against "
                "symlink-based TOCTOU attacks or symlinks inside base_dir that "
                "point outside. For maximum security, use a dedicated filesystem "
                "namespace or container-level isolation. Only enable this in "
                "fully trusted environments."
            )

        self.operations = FileSystemOperations()

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        """
        SSOT for service input normalization.
        Coerces input to Path AND anchors it to the service's base_dir with sandboxing.
        """
        try:
            return coerce_path(
                path,
                base_dir=self.base_dir,
                allow_absolute=self.unsafe_allow_absolute_paths,
            )
        except (QuackPathEscapeError, QuackPathOutsideBaseDirError) as e:
            # Re-raise sandbox violations to be mapped to specific error types
            raise e
        except ValueError as e:
            # Wrap standard coercion errors in QuackValidationError
            raise QuackValidationError(
                f"Invalid path input: {path}", original_error=e
            ) from e
        except TypeError as e:
            # Wrap shape/type errors
            raise QuackValidationError(
                f"Invalid path input type: {path}", original_error=e
            ) from e
        except Exception as e:
            raise QuackValidationError(
                f"Invalid path input: {path}", original_error=e
            ) from e

    # Ordered exception-type dispatch table for _map_error. ORDER MATTERS: the
    # first matching (most-specific-first) entry wins, exactly mirroring the
    # prior if/elif isinstance chain's semantics. ValueError is handled
    # separately below because its disposition depends on the message text,
    # not just the type.
    _ERROR_TYPE_DISPATCH: tuple[tuple[type[Exception], str, str], ...] = (
        (
            QuackPathEscapeError,
            "path_escape_attempt",
            "Path attempted to traverse above the base directory using '..' or "
            "similar.",
        ),
        (
            QuackPathOutsideBaseDirError,
            "path_outside_base_dir",
            "Absolute paths outside the configured base directory are not allowed "
            "(unsafe_allow_absolute_paths=False).",
        ),
        (
            QuackValidationError,
            "validation_error",
            "The input path is invalid, malformed, or unsafe.",
        ),
        (TypeError, "validation_error", "Invalid path input type or shape."),
        (
            FileNotFoundError,
            "file_not_found",
            "Check if the file path is correct relative to base_dir.",
        ),
        (
            FileExistsError,
            "file_exists",
            "Target already exists. Use overwrite=True or choose a different path.",
        ),
        (
            PermissionError,
            "permission_denied",
            "Check file permissions or run with elevated privileges.",
        ),
        (
            IsADirectoryError,
            "is_a_directory",
            "Expected a file but found a directory.",
        ),
        (
            NotADirectoryError,
            "not_a_directory",
            "Expected a directory but found a file.",
        ),
        (
            OSError,
            "io_error",
            "An operating system error occurred during filesystem access.",
        ),
    )

    @staticmethod
    def _map_value_error(msg: str) -> tuple[str, str]:
        """
        Sub-dispatch for ValueError, whose disposition depends on message text
        rather than a distinct exception subclass. Extracted from _map_error
        to keep the top-level dispatch a flat table (C901 reduction).
        """
        msg_lower = msg.lower()
        if "unsupported algorithm" in msg_lower:
            return "unsupported_algorithm", "Check the requested hash algorithm."
        if "invalid regex" in msg_lower:
            return (
                "invalid_regex",
                "The provided regular expression pattern is invalid.",
            )
        if "is not a dict" in msg_lower:  # yaml/json parsing errors from ops
            return (
                "invalid_data_format",
                "The file content structure does not match the expected format "
                "(e.g. dict).",
            )
        return "validation_error", "Input validation failed."

    def _map_error(self, e: Exception) -> ErrorInfo:
        """
        Centralized error mapping logic.
        Converts native exceptions to structured ErrorInfo with stable IDs.

        CRITICAL: Order matters - most specific exceptions first! See
        _ERROR_TYPE_DISPATCH for the ordered type table; ValueError is
        special-cased via _map_value_error because its mapping depends on
        message content, not just its type.
        """
        exception_cls = e.__class__.__name__
        msg = str(e)
        trace_id = str(uuid.uuid4())

        err_type = "unknown_error"
        hint: str | None = None

        for exc_type, mapped_type, mapped_hint in self._ERROR_TYPE_DISPATCH:
            if isinstance(e, exc_type):
                err_type, hint = mapped_type, mapped_hint
                break
        else:
            # No entry in the table matched - only ValueError has a mapping
            # left to try (checked last, same as the original elif chain).
            if isinstance(e, ValueError):
                err_type, hint = self._map_value_error(msg)

        details = {}
        if hasattr(e, "filename"):
            details["filename"] = str(e.filename)
        if hasattr(e, "errno"):
            details["errno"] = e.errno

        return ErrorInfo(
            type=err_type,
            message=msg,
            hint=hint,
            exception=exception_cls,
            trace_id=trace_id,
            details=details if details else None,
        )
