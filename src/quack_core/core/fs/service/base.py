# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/base.py
# module: quack_core.core.fs.service.base
# role: service
# neighbors: __init__.py, directory_operations.py, factory.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: FileSystemService
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/service/base.py
"""
Base class for the FileSystemService.

This provides the core functionality and initialization for the service.
"""

from pathlib import Path

from quack_core.fs._helpers.path_utils import _extract_path_str, _safe_path_str
from quack_core.fs._operations import FileSystemOperations
from quack_core.fs.results import DataResult, OperationResult
from quack_core.logging import LOG_LEVELS, LogLevel, get_logger


class FileSystemService:
    """
    High-level service for filesystem _operations.

    This service provides a clean, consistent API for all file _operations
    in QuackCore, with proper error handling and result objects.
    """

    def __init__(
            self,
            base_dir: str | Path | None = None,
            log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """
        Initialize the filesystem service.

        Args:
            base_dir: Optional base directory for relative paths
                      (default: current working directory)
            log_level: Logging level for the service
        """
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)

        # Initialize _operations with base directory
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.operations = FileSystemOperations(self.base_dir)

    def _normalize_input_path(
            self, path: str | Path | DataResult | OperationResult
    ) -> Path:
        """
        Normalize an input path to a clean, safe Path object.

        This method extracts, unwraps, and validates the path-like input, falling back to
        the base directory if the result is invalid or non-path-compatible.
        """
        try:
            if hasattr(path, "path") and path.path is not None:
                raw_path = path.path
            elif hasattr(path, "data") and path.data is not None:
                raw_path = path.data
            else:
                raw_path = path

            # Normalize and safely convert
            raw_str = _extract_path_str(raw_path)
            safe_str = _safe_path_str(raw_str)
            if safe_str:
                return Path(safe_str)

        except Exception as e:
            self.logger.warning(f"[normalize_input_path] Failed on path: {path} — {e}")

        self.logger.warning(
            f"[normalize_input_path] Falling back to base_dir: {self.base_dir}")
        return self.base_dir
