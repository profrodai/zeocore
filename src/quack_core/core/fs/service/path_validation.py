from pathlib import Path
from typing import Any
from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.results import DataResult, PathResult, ErrorInfo, BoolResult
from quack_core.core.fs.normalize import coerce_path_str


class PathValidationMixin:
    operations: FileSystemOperations
    logger: Any

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        raise NotImplementedError

    def _map_error(self, e: Exception) -> ErrorInfo:
        raise NotImplementedError

    def path_exists(self, path: FsPathLike) -> BoolResult:
        try:
            normalized_path = self._normalize_input_path(path)
            exists = self.operations._path_exists(normalized_path)
            return BoolResult(ok=True, path=normalized_path, value=exists,
                              message=f"Path {'exists' if exists else 'does not exist'}")
        except Exception as e:
            return BoolResult(
                ok=False,
                path=None,
                value=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to check existence"
            )

    def is_valid_path(self, path: FsPathLike) -> BoolResult:
        """
        Checks if the input is syntactically valid as a path string.
        Does NOT normalize or check for sandbox safety.
        """
        try:
            path_str = coerce_path_str(path)
            is_valid = self.operations._is_path_syntax_valid(path_str)
            return BoolResult(ok=True, path=None, value=is_valid,
                              message=f"Syntax is {'valid' if is_valid else 'invalid'}")
        except Exception as e:
            return BoolResult(
                ok=False,
                path=None,
                value=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to check syntax"
            )

    def is_safe_path(self, path: FsPathLike) -> BoolResult:
        """
        Checks if the path is safe (valid AND anchored within base_dir).
        Returns ok=True, value=True if safe.
        Returns ok=False, value=False if unsafe (sandbox violation).
        """
        try:
            norm_path = self._normalize_input_path(path)
            return BoolResult(ok=True, path=norm_path, value=True, message="Path is safe and anchored")
        except Exception as e:
            return BoolResult(
                ok=False,
                path=None,
                value=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Path is unsafe or invalid"
            )

    def validate_path(self, path: FsPathLike) -> BoolResult:
        """
        Strictly validates that a path is safe, absolute (after normalization), and syntactically valid.
        Does NOT check existence.
        Alias for is_safe_path, provided for architectural alignment.
        """
        return self.is_safe_path(path)

    def validate_file(self, path: FsPathLike) -> BoolResult:
        """
        Strictly validates that a path is safe and currently points to a file.
        """
        try:
            norm_path = self._normalize_input_path(path)
            if not self.operations._path_exists(norm_path):
                return BoolResult(ok=False, path=norm_path, value=False, error="File does not exist",
                                  message="File does not exist")

            # Using _get_file_info to check if it's a file without extra IO ops if possible,
            # or just calling is_file from operations if available (FileInfo is safer)
            info = self.operations._get_file_info(norm_path)
            if not info.is_file:
                return BoolResult(ok=False, path=norm_path, value=False, error="Path is not a file",
                                  message="Path exists but is not a file")

            return BoolResult(ok=True, path=norm_path, value=True, message="Path is a valid file")
        except Exception as e:
            return BoolResult(
                ok=False,
                path=None,
                value=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Validation failed"
            )

    def normalize_path_with_info(self, path: FsPathLike) -> PathResult:
        try:
            normalized_path = self._normalize_input_path(path)
            # Use _resolve_path (strict=False) which is equivalent to non-strict normalization logic
            # previously handled by a separate normalize method in Ops.
            result_path = self.operations._resolve_path(normalized_path, strict=False)
            exists = self.operations._path_exists(result_path)
            return PathResult(ok=True, path=result_path, is_absolute=result_path.is_absolute(), is_valid=True,
                              exists=exists, message="Normalized path")
        except Exception as e:
            return PathResult(
                ok=False,
                path=None,
                is_valid=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Normalization failed"
            )

    def resolve_path_strict(self, path: FsPathLike) -> PathResult:
        try:
            normalized_path = self._normalize_input_path(path)
            # Use strict=True for real strict resolution (raises FileNotFoundError if missing)
            resolved = self.operations._resolve_path(normalized_path, strict=True)
            return PathResult(ok=True, path=resolved, is_absolute=True, is_valid=True, exists=True,
                              message="Resolved existing path")
        except FileNotFoundError:
            # Handle specifically to return clean result
            # We can re-resolve non-strictly to get the path for the result object
            non_strict_path = self.operations._resolve_path(normalized_path, strict=False)
            return PathResult(ok=False, path=non_strict_path, is_valid=True, exists=False, error="Path does not exist",
                              message="Resolved but not found")
        except Exception as e:
            return PathResult(
                ok=False,
                path=None,
                is_valid=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Resolution failed"
            )