# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/path_operations.py
# module: quack_core.core.fs.service.path_operations
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+4 more)
# exports: PathOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

from pathlib import Path
from typing import Any
from quack_core.core.fs.operations.base import FileSystemOperations
from quack_core.core.fs.results import DataResult, PathResult, ErrorInfo
from quack_core.core.fs.normalize import coerce_path_str, safe_path_str
from quack_core.core.fs.protocols import FsPathLike

class PathOperationsMixin:
    operations: FileSystemOperations
    logger: Any
    def _normalize_input_path(self, path: FsPathLike) -> Path: raise NotImplementedError
    def _map_error(self, e: Exception) -> ErrorInfo: raise NotImplementedError

    def join_path(self, *parts: FsPathLike) -> DataResult[str]:
        try:
            if not parts: return DataResult(success=True, path=Path("."), data=".", format="path", message="Empty join")
            str_parts = [coerce_path_str(p) for p in parts]
            base = str_parts[0]
            others = [p.lstrip("/\\") for p in str_parts[1:]]
            joined = Path(base).joinpath(*others)
            return DataResult(success=True, path=joined, data=str(joined), format="path", message="Joined paths")
        except Exception as e:
            return DataResult(
                success=False,
                path=None,
                data="",
                format="path",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to join paths"
            )

    def split_path(self, path: FsPathLike) -> DataResult[list[str]]:
        try:
            norm_path = self._normalize_input_path(path)
            components = self.operations._split_path(norm_path)
            return DataResult(success=True, path=norm_path, data=components, format="path_components", message=f"Split {len(components)} components")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data=[],
                format="path_components",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to split path"
            )

    def normalize_path(self, path: FsPathLike) -> PathResult:
        try:
            norm_path = self._normalize_input_path(path)
            res_path = self.operations._normalize_path(norm_path)
            return PathResult(success=True, path=res_path, is_absolute=res_path.is_absolute(), is_valid=True, exists=res_path.exists(), message=f"Normalized: {res_path}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return PathResult(
                success=False,
                path=safe_p,
                is_valid=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to normalize path"
            )

    def expand_user_vars(self, path: FsPathLike) -> DataResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            expanded = self.operations._expand_user_vars(norm_path)
            return DataResult(success=True, path=norm_path, data=expanded, format="path", message=f"Expanded: {expanded}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data="",
                format="path",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to expand variables"
            )

    def is_same_file(self, path1: FsPathLike, path2: FsPathLike) -> DataResult[bool]:
        try:
            p1 = self._normalize_input_path(path1)
            p2 = self._normalize_input_path(path2)
            same = self.operations._is_same_file(p1, p2)
            return DataResult(success=True, path=p1, data=same, format="boolean", message="Checked identity")
        except Exception as e:
            return DataResult(
                success=False,
                path=None,
                data=False,
                format="boolean",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to compare files"
            )

    def is_subdirectory(self, child: FsPathLike, parent: FsPathLike) -> DataResult[bool]:
        try:
            c = self._normalize_input_path(child)
            p = self._normalize_input_path(parent)
            is_sub = self.operations._is_subdirectory(c, p)
            return DataResult(success=True, path=c, data=is_sub, format="boolean", message="Checked subdirectory")
        except Exception as e:
            safe_p_str = safe_path_str(child)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data=False,
                format="boolean",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to check subdirectory"
            )

    def create_temp_directory(self, prefix: str = "quackcore_", suffix: str = "") -> DataResult[str]:
        try:
            temp_dir = self.operations._create_temp_directory(prefix, suffix)
            return DataResult(success=True, path=temp_dir, data=str(temp_dir), format="path", message=f"Created temp dir: {temp_dir}")
        except Exception as e:
            return DataResult(
                success=False,
                path=None,
                data="",
                format="path",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to create temp directory"
            )

    def get_extension(self, path: FsPathLike) -> DataResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            ext = self.operations._get_extension(norm_path)
            return DataResult(success=True, path=norm_path, data=ext, format="extension", message=f"Extension: {ext}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return DataResult(
                success=False,
                path=safe_p,
                data="",
                format="extension",
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to extract extension"
            )

    def resolve_path(self, path: FsPathLike) -> PathResult:
        try:
            norm_path = self._normalize_input_path(path)
            res = self.operations._resolve_path(norm_path)
            return PathResult(success=True, path=res, is_absolute=res.is_absolute(), is_valid=True, exists=res.exists(), message=f"Resolved: {res}")
        except Exception as e:
            safe_p_str = safe_path_str(path)
            safe_p = Path(safe_p_str) if safe_p_str else None
            return PathResult(
                success=False,
                path=safe_p,
                is_valid=False,
                error_info=self._map_error(e),
                error=str(e),
                message="Failed to resolve path"
            )