# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/base.py
# module: quack_core.core.fs.service.base
# role: service
# neighbors: __init__.py, directory_operations.py, factory.py, file_operations.py, full_class.py, path_operations.py (+4 more)
# exports: FileSystemService
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

from pathlib import Path

from quack_core.core.fs.operations.base import FileSystemOperations
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from quack_core.core.errors import QuackValidationError
from quack_core.core.fs._internal.path_utils import _extract_path_str

class FileSystemService:
    """Central FileSystem Service."""
    def __init__(self, base_dir: str | Path | None = None, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.operations = FileSystemOperations(self.base_dir)

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        """
        SSOT for service input normalization.
        Extracts path string from polymorphic input and returns a Path object.
        """
        try:
            # We use the internal helper here because this is the service implementation details
            # Callers should not need to know about _extract_path_str
            path_str = _extract_path_str(path)
            return Path(path_str)
        except (TypeError, ValueError) as e:
            raise QuackValidationError(f"Invalid path input: {path}", original_error=e) from e