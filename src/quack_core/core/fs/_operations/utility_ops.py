# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/utility_ops.py
# module: quack_core.core.fs._operations.utility_ops
# role: module
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: UtilityOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from pathlib import Path

class UtilityOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _compute_checksum(self, path: str | Path, algorithm: str = "sha256") -> str:
        from quack_core.core.fs._helpers.checksums import _compute_checksum
        resolved = self._resolve_path(path)
        return _compute_checksum(resolved, algorithm)

    def _create_temp_file(self, suffix: str, prefix: str, directory: Path | None) -> Path:
        from quack_core.core.fs._helpers.temp import _create_temp_file
        # resolved_dir logic might be needed if directory is not None
        # Helpers handle Path objects fine.
        return _create_temp_file(suffix, prefix, directory)

    def _create_temp_directory(self, prefix: str, suffix: str) -> Path:
        from quack_core.core.fs._helpers.temp import _create_temp_directory
        return _create_temp_directory(prefix, suffix)

    def _get_unique_filename(self, directory: str | Path, filename: str) -> Path:
        from quack_core.core.fs._helpers.file_ops import _get_unique_filename
        resolved = self._resolve_path(directory)
        return _get_unique_filename(resolved, filename)

    def _ensure_directory(self, path: str | Path, exist_ok: bool = True) -> Path:
        from quack_core.core.fs._helpers.file_ops import _ensure_directory
        return _ensure_directory(self._resolve_path(path), exist_ok)

    def _get_disk_usage(self, path: str | Path) -> dict[str, int]:
        from quack_core.core.fs._helpers.disk import _get_disk_usage
        return _get_disk_usage(self._resolve_path(path))

    def _get_file_size_str(self, size_bytes: int) -> str:
        from quack_core.core.fs._helpers.file_info import _get_file_size_str
        return _get_file_size_str(size_bytes)

    def _get_file_timestamp(self, path: str | Path) -> float:
        from quack_core.core.fs._helpers.file_info import _get_file_timestamp
        return _get_file_timestamp(self._resolve_path(path))

    def _get_file_type(self, path: str | Path) -> str:
        from quack_core.core.fs._helpers.file_info import _get_file_type
        return _get_file_type(self._resolve_path(path))

    def _get_mime_type(self, path: str | Path) -> str | None:
        from quack_core.core.fs._helpers.file_info import _get_mime_type
        return _get_mime_type(self._resolve_path(path))

    def _is_path_writeable(self, path: str | Path) -> bool:
        from quack_core.core.fs._helpers.disk import _is_path_writeable
        return _is_path_writeable(self._resolve_path(path))

    def _is_file_locked(self, path: str | Path) -> bool:
        from quack_core.core.fs._helpers.file_info import _is_file_locked
        return _is_file_locked(self._resolve_path(path))

    def _find_files_by_content(self, directory: str | Path, text_pattern: str, recursive: bool) -> list[Path]:
        from quack_core.core.fs._helpers.file_ops import _find_files_by_content
        return _find_files_by_content(self._resolve_path(directory), text_pattern, recursive)