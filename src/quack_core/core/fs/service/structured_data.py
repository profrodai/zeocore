# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/structured_data.py
# module: quack_core.core.fs.service.structured_data
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+4 more)
# exports: StructuredDataMixin
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

from pathlib import Path
from typing import Any
from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.results import DataResult, WriteResult, ErrorInfo
from quack_core.core.fs.normalize import safe_path_str

class StructuredDataMixin:
    operations: FileSystemOperations
    logger: Any
    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError
    def _map_error(self, e: Exception) -> ErrorInfo: raise NotImplementedError

    def read_yaml(self, path: FsPathLike) -> DataResult[dict]:
        try:
            normalized_path = self._normalize_input_path(path)
            data = self.operations._read_yaml(normalized_path)
            self.logger.debug(f"Read YAML from {normalized_path}")
            if not isinstance(data, dict):
                return DataResult(success=False, path=normalized_path, data={}, format="yaml", error=f"YAML content was not a dictionary (got {type(data)})", message="Invalid YAML structure")
            return DataResult(success=True, path=normalized_path, data=data, format="yaml", message="Read YAML")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data={},
                format="yaml",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read YAML"
            )

    def write_yaml(self, path: FsPathLike, data: dict, atomic: bool = True) -> WriteResult:
        try:
            normalized_path = self._normalize_input_path(path)
            result_path = self.operations._write_yaml(normalized_path, data, atomic)
            self.logger.debug(f"Wrote YAML to {result_path}")
            return WriteResult(success=True, path=result_path, message="Wrote YAML")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return WriteResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write YAML"
            )

    def read_json(self, path: FsPathLike) -> DataResult[dict]:
        try:
            normalized_path = self._normalize_input_path(path)
            data = self.operations._read_json(normalized_path)
            self.logger.debug(f"Read JSON from {normalized_path}")
            if not isinstance(data, dict):
                return DataResult(success=False, path=normalized_path, data={}, format="json", error=f"JSON content was not a dictionary (got {type(data)})", message="Invalid JSON structure")
            return DataResult(success=True, path=normalized_path, data=data, format="json", message="Read JSON")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data={},
                format="json",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read JSON"
            )

    def write_json(self, path: FsPathLike, data: dict, atomic: bool = True, indent: int = 2) -> WriteResult:
        try:
            normalized_path = self._normalize_input_path(path)
            result_path = self.operations._write_json(normalized_path, data, atomic, indent)
            self.logger.debug(f"Wrote JSON to {result_path}")
            return WriteResult(success=True, path=result_path, message="Wrote JSON")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return WriteResult(
                success=False,
                path=safe_p,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write JSON"
            )