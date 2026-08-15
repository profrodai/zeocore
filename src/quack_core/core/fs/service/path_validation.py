# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/path_validation.py
# module: quack_core.core.fs.service.path_validation
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_info_operations.py, file_operations.py (+5 more)
# exports: PathValidationMixin
# git_branch: feat/9-make-setup-work
# git_commit: f4879df3
# === QV-LLM:END ===

from pathlib import Path
from typing import Any

from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.normalize import coerce_path_str, safe_path_str
from quack_core.core.fs.protocols import FsPathLike
from quack_core.core.fs.results import BoolResult, ErrorInfo, PathResult


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
            return BoolResult(
                ok=True,
                path=normalized_path,
                value=exists,
                message=f"Path {'exists' if exists else 'does not exist'}",
            )
        except Exception as e:
            s = safe_path_str(path)
            return BoolResult(
                ok=False,
                path=None,
                value=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to check existence",
                meta={"input_path": s} if s else None,
            )

    def is_valid_path(self, path: FsPathLike) -> BoolResult:
        """
        Checks if the input is syntactically valid as a path string.
        Does NOT normalize or check for sandbox safety.

        For full validation (syntax + normalization + sandbox), use is_safe_path().
        """
        try:
            path_str = coerce_path_str(path)
            is_valid = self.operations._is_path_syntax_valid(path_str)
            return BoolResult(
                ok=True,
                path=None,
                value=is_valid,
                message=f"Syntax is {'valid' if is_valid else 'invalid'}",
            )
        except Exception as e:
            s = safe_path_str(path)
            return BoolResult(
                ok=False,
                path=None,
                value=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to check syntax",
                meta={"input_path": s} if s else None,
            )

    def is_safe_path(self, path: FsPathLike) -> BoolResult:
        """
        Checks if the path is safe (valid AND anchored within base_dir).
        Returns ok=True, value=True if safe.
        Returns ok=False, value=False if unsafe (sandbox violation).
        """
        try:
            norm_path = self._normalize_input_path(path)
            return BoolResult(
                ok=True, path=norm_path, value=True, message="Path is safe and anchored"
            )
        except Exception as e:
            s = safe_path_str(path)
            return BoolResult(
                ok=False,
                path=None,
                value=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Path is unsafe or invalid",
                meta={"input_path": s} if s else None,
            )

    def validate_path(self, path: FsPathLike) -> BoolResult:
        """
        Strictly validates that a path is safe, absolute (after normalization), and syntactically valid.
        Does NOT check existence.
        Alias for is_safe_path(), provided for architectural alignment.
        """
        return self.is_safe_path(path)

    def validate_file(self, path: FsPathLike) -> BoolResult:
        """
        Strictly validates that a path is safe and currently points to a file.
        """
        try:
            norm_path = self._normalize_input_path(path)
            if not self.operations._path_exists(norm_path):
                return BoolResult(
                    ok=False,
                    path=norm_path,
                    value=False,
                    error="File does not exist",
                    message="File does not exist",
                )

            info = self.operations._get_file_info(norm_path)
            if not info.is_file:
                return BoolResult(
                    ok=False,
                    path=norm_path,
                    value=False,
                    error="Path is not a file",
                    message="Path exists but is not a file",
                )

            return BoolResult(
                ok=True, path=norm_path, value=True, message="Path is a valid file"
            )
        except Exception as e:
            s = safe_path_str(path)
            return BoolResult(
                ok=False,
                path=None,
                value=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Validation failed",
                meta={"input_path": s} if s else None,
            )

    def normalize_path_with_info(self, path: FsPathLike) -> PathResult:
        try:
            normalized_path = self._normalize_input_path(path)
            result_path = self.operations._resolve_path(normalized_path, strict=False)
            exists = self.operations._path_exists(result_path)
            return PathResult(
                ok=True,
                path=result_path,
                is_absolute=result_path.is_absolute(),
                is_valid=True,
                exists=exists,
                message="Normalized path",
            )
        except Exception as e:
            s = safe_path_str(path)
            return PathResult(
                ok=False,
                path=None,
                is_valid=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Normalization failed",
                meta={"input_path": s} if s else None,
            )

    def resolve_path_strict(self, path: FsPathLike) -> PathResult:
        """
        Resolve path with strict mode: MUST exist.

        Result Semantics:
            ok=False, is_valid=True, exists=False:
                Path normalization/sandbox succeeded, but path doesn't exist.
                error_info.type will be 'file_not_found'.

            ok=False, is_valid=False:
                Path normalization/sandbox failed.
                error_info.type will be 'validation_error' or 'path_escape_attempt'.

        This follows the doctrine: ok=False for any failure, but is_valid
        distinguishes "bad path" from "path doesn't exist".
        """
        normalized_path = None
        try:
            normalized_path = self._normalize_input_path(path)
            # strict=True raises FileNotFoundError if missing
            resolved = self.operations._resolve_path(normalized_path, strict=True)
            return PathResult(
                ok=True,
                path=resolved,
                is_absolute=True,
                is_valid=True,
                exists=True,
                message="Resolved existing path",
            )
        except FileNotFoundError:
            # Normalization succeeded, but path doesn't exist
            # This is ok=False (operation goal failed) but is_valid=True (path is safe)
            if normalized_path:
                try:
                    non_strict_path = self.operations._resolve_path(
                        normalized_path, strict=False
                    )
                    return PathResult(
                        ok=False,
                        path=non_strict_path,
                        is_valid=True,  # Path is valid/safe, just doesn't exist
                        exists=False,
                        error="Path does not exist",
                        error_info=self._map_error(
                            FileNotFoundError(str(normalized_path))
                        ),
                        message="Resolved but not found",
                    )
                except Exception:
                    s = safe_path_str(path)
                    return PathResult(
                        ok=False,
                        path=None,
                        is_valid=True,
                        exists=False,
                        error="Path does not exist",
                        message="Resolved but not found",
                        meta={"input_path": s} if s else None,
                    )
            else:
                s = safe_path_str(path)
                return PathResult(
                    ok=False,
                    path=None,
                    is_valid=True,
                    exists=False,
                    error="Path does not exist",
                    message="Resolved but not found",
                    meta={"input_path": s} if s else None,
                )
        except Exception as e:
            # Normalization failed (bad path / sandbox violation)
            # This is ok=False AND is_valid=False
            s = safe_path_str(path)
            return PathResult(
                ok=False,
                path=None,
                is_valid=False,  # Path failed validation
                error_info=self._map_error(e),
                error=str(e),
                message="Resolution failed",
                meta={"input_path": s} if s else None,
            )
