from pathlib import Path
from typing import Any
from quack_core.fs.operations.base import FileSystemOperations
from quack_core.fs.results import DirectoryInfoResult, FindResult, OperationResult, \
    FileInfoResult
from quack_core.fs.protocols import FsPathLike
from quack_core.fs.normalize import safe_path_str


class DirectoryOperationsMixin:
    operations: FileSystemOperations
    logger: Any

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        raise NotImplementedError

    def _map_error(self, e: Exception) -> Any:
        raise NotImplementedError

    def create_directory(self, path: FsPathLike,
                         exist_ok: bool = True) -> OperationResult:
        try:
            normalized_path = self._normalize_input_path(path)
            result_path = self.operations._ensure_directory(normalized_path, exist_ok)
            return OperationResult(success=True, path=result_path,
                                   message=f"Directory created: {result_path}")
        except Exception as e:
            self.logger.error(f"Error creating directory: {e}")
            safe_p = Path(safe_path_str(path) or "")
            return OperationResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to create directory"
            )

    # ... (Other methods updated similarly)