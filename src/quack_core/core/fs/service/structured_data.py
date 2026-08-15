# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/structured_data.py
# module: quack_core.core.fs.service.structured_data
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_info_operations.py, file_operations.py (+5 more)
# exports: StructuredDataMixin
# git_branch: main
# git_commit: f0715f0c
# === QV-LLM:END ===


from pathlib import Path
from typing import Any

from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.normalize import safe_path_str
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.results import DataResult, ErrorInfo, WriteResult


class StructuredDataMixin:
    operations: FileSystemOperations
    logger: Any

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        raise NotImplementedError

    def _map_error(self, e: Exception) -> ErrorInfo:
        raise NotImplementedError

    def read_yaml(self, path: FsPathLike) -> DataResult[dict[str, Any]]:
        try:
            normalized_path = self._normalize_input_path(path)
            data = self.operations._read_yaml(normalized_path)
            self.logger.debug(f"Read YAML from {normalized_path}")
            if not isinstance(data, dict):
                return DataResult(
                    ok=False,
                    path=normalized_path,
                    data=None,
                    format="yaml",
                    error=f"YAML content was not a dictionary (got {type(data)})",
                    message="Invalid YAML structure",
                )
            return DataResult(
                ok=True,
                path=normalized_path,
                data=data,
                format="yaml",
                message="Read YAML",
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data=None,
                format="yaml",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read YAML",
                meta={"input_path": s} if s else None,
            )

    def write_yaml(
        self, path: FsPathLike, data: dict[str, Any], atomic: bool = True
    ) -> WriteResult:
        try:
            normalized_path = self._normalize_input_path(path)
            result_path = self.operations._write_yaml(normalized_path, data, atomic)
            self.logger.debug(f"Wrote YAML to {result_path}")
            return WriteResult(ok=True, path=result_path, message="Wrote YAML")
        except Exception as e:
            s = safe_path_str(path)
            return WriteResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write YAML",
                meta={"input_path": s} if s else None,
            )

    def read_json(self, path: FsPathLike) -> DataResult[dict[str, Any]]:
        try:
            normalized_path = self._normalize_input_path(path)
            data = self.operations._read_json(normalized_path)
            self.logger.debug(f"Read JSON from {normalized_path}")
            if not isinstance(data, dict):
                return DataResult(
                    ok=False,
                    path=normalized_path,
                    data=None,
                    format="json",
                    error=f"JSON content was not a dictionary (got {type(data)})",
                    message="Invalid JSON structure",
                )
            return DataResult(
                ok=True,
                path=normalized_path,
                data=data,
                format="json",
                message="Read JSON",
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False,
                path=None,
                data=None,
                format="json",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to read JSON",
                meta={"input_path": s} if s else None,
            )

    def write_json(
        self,
        path: FsPathLike,
        data: dict[str, Any],
        atomic: bool = True,
        indent: int = 2,
    ) -> WriteResult:
        try:
            normalized_path = self._normalize_input_path(path)
            result_path = self.operations._write_json(
                normalized_path, data, atomic, indent
            )
            self.logger.debug(f"Wrote JSON to {result_path}")
            return WriteResult(ok=True, path=result_path, message="Wrote JSON")
        except Exception as e:
            s = safe_path_str(path)
            return WriteResult(
                ok=False,
                path=None,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to write JSON",
                meta={"input_path": s} if s else None,
            )
