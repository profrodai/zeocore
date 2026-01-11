# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/find_ops.py
# module: quack_core.core.fs._ops.find_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, path_ops.py (+4 more)
# exports: FindOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

from pathlib import Path


class FindOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _find_files(self, path: str | Path, pattern: str, recursive: bool = True, include_hidden: bool = False) -> \
    tuple[list[Path], list[Path]]:
        resolved = self._resolve_path(path)
        if not resolved.exists() or not resolved.is_dir():
            raise NotADirectoryError(f"Invalid search directory: {resolved}")

        files: list[Path] = []
        directories: list[Path] = []
        iterator = resolved.rglob(pattern) if recursive else resolved.glob(pattern)

        for item in iterator:
            if not include_hidden and item.name.startswith("."): continue
            try:
                if item.is_file():
                    files.append(item)
                elif item.is_dir():
                    directories.append(item)
            except OSError:
                continue
        return files, directories