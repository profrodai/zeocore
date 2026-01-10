# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/path_validation.py
# module: quack_core.core.fs.service.path_validation
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+4 more)
# exports: PathValidationMixin
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

from pathlib import Path
from typing import Any
from quack_core.core.fs.operations.base import FileSystemOperations
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.results import DataResult, PathResult
from quack_core.core.fs.api.public.coerce import coerce_path_result

class PathValidationMixin:
    operations: FileSystemOperations
    logger: Any

    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError

    def path_exists(self, path: FsPathLike) -> DataResult[bool]:
        try:
            normalized_path = self._normalize_input_path(path)
            exists = self.operations._path_exists(normalized_path)
            return DataResult(success=True, path=normalized_path, data=exists, format="boolean", message=f"Path {'exists' if exists else 'does not exist'}")
        except Exception as e:
            self.logger.error(f"Error checking existence for {path}: {e}")
            safe_p = coerce_path_result(path)
            return DataResult(success=False, path=safe_p.path if safe_p.success else None, data=False, format="boolean", error=str(e), message="Failed to check existence")

    def is_valid_path(self, path: FsPathLike) -> DataResult[bool]:
        try:
            normalized_path = self._normalize_input_path(path)
            is_valid = self.operations._is_path_syntax_valid(str(normalized_path))
            return DataResult(success=True, path=normalized_path, data=is_valid, format="boolean", message=f"Syntax is {'valid' if is_valid else 'invalid'}")
        except Exception as e:
            self.logger.error(f"Error checking syntax for {path}: {e}")
            safe_p = coerce_path_result(path)
            return DataResult(success=False, path=safe_p.path if safe_p.success else None, data=False, format="boolean", error=str(e), message="Failed to check syntax")

    def normalize_path_with_info(self, path: FsPathLike) -> PathResult:
        try:
            normalized_path = self._normalize_input_path(path)
            result_path = self.operations._normalize_path(normalized_path)
            exists = self.operations._path_exists(result_path)
            return PathResult(success=True, path=result_path, is_absolute=result_path.is_absolute(), is_valid=True, exists=exists, message="Normalized path")
        except Exception as e:
            self.logger.error(f"Error normalizing {path}: {e}")
            safe_p = coerce_path_result(path)
            return PathResult(success=False, path=safe_p.path if safe_p.success else None, is_valid=False, error=str(e), message="Normalization failed")

    def resolve_path_strict(self, path: FsPathLike) -> PathResult:
        try:
            normalized_path = self._normalize_input_path(path)
            resolved = self.operations._resolve_path(normalized_path)
            if not resolved.exists():
                return PathResult(success=False, path=resolved, is_valid=True, exists=False, error="Path does not exist", message="Resolved but not found")
            return PathResult(success=True, path=resolved, is_absolute=True, is_valid=True, exists=True, message="Resolved existing path")
        except Exception as e:
            self.logger.error(f"Error resolving {path}: {e}")
            safe_p = coerce_path_result(path)
            return PathResult(success=False, path=safe_p.path if safe_p.success else None, is_valid=False, error=str(e), message="Resolution failed")