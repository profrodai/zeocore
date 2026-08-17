from pathlib import Path

from quack_core.core.fs._internal.common import _get_extension
from quack_core.core.fs._internal.comparison import _is_same_file, _is_subdirectory
from quack_core.core.fs._internal.path_ops import (
    _expand_user_vars,
    _is_path_syntax_valid,
    _resolve_path,
    _split_path,
)


class PathOperationsMixin:
    def _split_path(self, path: Path) -> list[str]:
        return _split_path(path)

    def _expand_user_vars(self, path: Path) -> Path:
        """
        Expand user vars from a Path.
        _ops layer: Path in, Path out (service decides stringification).
        """
        return _expand_user_vars(path)

    def _is_same_file(self, path1: Path, path2: Path) -> bool:
        return _is_same_file(path1, path2)

    def _is_subdirectory(self, child: Path, parent: Path) -> bool:
        return _is_subdirectory(child, parent)

    def _get_extension(self, path: Path) -> str:
        return _get_extension(path)

    def _resolve_path(self, path: Path, strict: bool = False) -> Path:
        return _resolve_path(path, strict=strict)

    def _is_path_syntax_valid(self, path_str: str) -> bool:
        return _is_path_syntax_valid(path_str)
