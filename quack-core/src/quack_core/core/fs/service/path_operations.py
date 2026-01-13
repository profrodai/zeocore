# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/path_operations.py
# module: quack_core.core.fs.service.path_operations
# role: service
# VERSION: V6 FINAL - Renamed expand_user_vars_raw, collapsed normalize/resolve
# === QV-LLM:END ===

from pathlib import Path
from typing import Any
from quack_core.core.fs._ops.base import FileSystemOperations
from quack_core.core.fs.results import DataResult, PathResult, ErrorInfo
from quack_core.core.fs.normalize import coerce_path_str, safe_path_str
from quack_core.core.fs.protocols import FsPathLike


class PathOperationsMixin:
    operations: FileSystemOperations
    logger: Any

    def _normalize_input_path(self, path: FsPathLike) -> Path:
        raise NotImplementedError

    def _map_error(self, e: Exception) -> ErrorInfo:
        raise NotImplementedError

    def join_path(self, *parts: FsPathLike) -> DataResult[str]:
        try:
            if not parts:
                return DataResult(ok=True, path=Path("."), data=".", format="path", message="Empty join")
            str_parts = [coerce_path_str(p) for p in parts]
            base = str_parts[0]
            others = [p.lstrip("/\\") for p in str_parts[1:]]

            joined_str = str(Path(base).joinpath(*others))
            norm_path = self._normalize_input_path(joined_str)

            return DataResult(ok=True, path=norm_path, data=str(norm_path), format="path", message="Joined paths")
        except Exception as e:
            return DataResult(
                ok=False, path=None, data="", format="path",
                error_info=self._map_error(e), error=str(e),
                message="Failed to join paths"
            )

    def split_path(self, path: FsPathLike) -> DataResult[list[str]]:
        try:
            norm_path = self._normalize_input_path(path)
            components = self.operations._split_path(norm_path)
            return DataResult(
                ok=True, path=norm_path, data=components, format="path_components",
                message=f"Split {len(components)} components"
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False, path=None, data=[], format="path_components",
                error_info=self._map_error(e), error=str(e),
                message="Failed to split path",
                meta={"input_path": s} if s else None
            )

    def normalize_path(self, path: FsPathLike) -> PathResult:
        """
        Normalize and anchor path to base_dir with sandbox checks.
        The path may or may not exist on the filesystem.
        """
        try:
            norm_path = self._normalize_input_path(path)
            res_path = self.operations._resolve_path(norm_path)
            return PathResult(
                ok=True, path=res_path,
                is_absolute=res_path.is_absolute(),
                is_valid=True,
                exists=res_path.exists(),
                message=f"Normalized: {res_path}"
            )
        except Exception as e:
            s = safe_path_str(path)
            return PathResult(
                ok=False, path=None, is_valid=False,
                error_info=self._map_error(e), error=str(e),
                message="Failed to normalize path",
                meta={"input_path": s} if s else None
            )

    def resolve_path(self, path: FsPathLike) -> PathResult:
        """
        Alias for normalize_path().
        Kept for backward compatibility.
        """
        return self.normalize_path(path)

    def expand_user_vars_raw(self, path: FsPathLike) -> DataResult[str]:
        """
        Expand ~ and environment variables in path string.

        Returns expanded path as string WITHOUT normalizing to base_dir.
        This is a raw utility function - the result is not anchored or sandboxed.

        Use normalize_path() if you need base_dir anchoring.
        """
        try:
            raw_path_str = coerce_path_str(path)
            expanded_path = self.operations._expand_user_vars(Path(raw_path_str))
            expanded_str = str(expanded_path)
            return DataResult(
                ok=True,
                path=None,  # Not normalized to base_dir - raw utility
                data=expanded_str,
                format="path",
                message=f"Expanded (raw): {expanded_str}"
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False, path=None, data="", format="path",
                error_info=self._map_error(e), error=str(e),
                message="Failed to expand variables",
                meta={"input_path": s} if s else None
            )

    # Legacy alias - to be deprecated
    def expand_user_vars(self, path: FsPathLike) -> DataResult[str]:
        """
        DEPRECATED: Use expand_user_vars_raw() for clarity.
        This is a raw expansion without base_dir anchoring.
        """
        return self.expand_user_vars_raw(path)

    def is_same_file(self, path1: FsPathLike, path2: FsPathLike) -> DataResult[bool]:
        try:
            p1 = self._normalize_input_path(path1)
            p2 = self._normalize_input_path(path2)
            same = self.operations._is_same_file(p1, p2)
            return DataResult(
                ok=True, path=p1, data=same, format="boolean",
                message="Checked identity"
            )
        except Exception as e:
            s1 = safe_path_str(path1)
            s2 = safe_path_str(path2)
            return DataResult(
                ok=False, path=None, data=False, format="boolean",
                error_info=self._map_error(e), error=str(e),
                message="Failed to compare files",
                meta={"input_path1": s1, "input_path2": s2} if (s1 or s2) else None
            )

    def is_subdirectory(self, child: FsPathLike, parent: FsPathLike) -> DataResult[bool]:
        try:
            c = self._normalize_input_path(child)
            p = self._normalize_input_path(parent)
            is_sub = self.operations._is_subdirectory(c, p)
            return DataResult(
                ok=True, path=c, data=is_sub, format="boolean",
                message="Checked subdirectory"
            )
        except Exception as e:
            s_child = safe_path_str(child)
            s_parent = safe_path_str(parent)
            return DataResult(
                ok=False, path=None, data=False, format="boolean",
                error_info=self._map_error(e), error=str(e),
                message="Failed to check subdirectory",
                meta={"input_child": s_child, "input_parent": s_parent} if (s_child or s_parent) else None
            )

    def get_extension(self, path: FsPathLike) -> DataResult[str]:
        try:
            norm_path = self._normalize_input_path(path)
            ext = self.operations._get_extension(norm_path)
            return DataResult(
                ok=True, path=norm_path, data=ext, format="extension",
                message=f"Extension: {ext}"
            )
        except Exception as e:
            s = safe_path_str(path)
            return DataResult(
                ok=False, path=None, data="", format="extension",
                error_info=self._map_error(e), error=str(e),
                message="Failed to extract extension",
                meta={"input_path": s} if s else None
            )