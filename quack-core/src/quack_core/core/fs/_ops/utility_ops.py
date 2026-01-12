# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/utility_ops.py
# module: quack_core.core.fs._ops.utility_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: UtilityOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 945fec3c
# === QV-LLM:END ===

from pathlib import Path
from quack_core.core.fs._internal.checksums import _compute_checksum
from quack_core.core.fs._internal.temp import _create_temp_file, _create_temp_directory
from quack_core.core.fs._internal.file_ops import _get_unique_filename, _find_files_by_content
from quack_core.core.fs._internal.directory_ops import _ensure_directory
from quack_core.core.fs._internal.disk import _get_disk_usage, _probe_path_writeable
from quack_core.core.fs._internal.file_info import _get_file_size_str, _get_file_timestamp, _get_file_type, _get_mime_type, _is_file_locked

class UtilityOperationsMixin:
    def _compute_checksum(self, path: Path, algorithm: str = "sha256") -> str:
        return _compute_checksum(path, algorithm)

    def _create_temp_file(self, suffix: str, prefix: str, directory: Path | None) -> Path:
        return _create_temp_file(suffix, prefix, directory)

    def _create_temp_directory(self, prefix: str, suffix: str, directory: Path | None) -> Path:
        return _create_temp_directory(prefix, suffix, directory)

    def _get_unique_filename(self, directory: Path, filename: str) -> Path:
        return _get_unique_filename(directory, filename)

    def _ensure_directory(self, path: Path, exist_ok: bool = True) -> Path:
        return _ensure_directory(path, exist_ok)

    def _get_disk_usage(self, path: Path) -> dict[str, int]:
        return _get_disk_usage(path)

    def _get_file_size_str(self, size_bytes: int) -> str:
        return _get_file_size_str(size_bytes)

    def _get_file_timestamp(self, path: Path) -> float:
        return _get_file_timestamp(path)

    def _get_file_type(self, path: Path) -> str:
        return _get_file_type(path)

    def _get_mime_type(self, path: Path) -> str | None:
        return _get_mime_type(path)

    def _is_path_writeable(self, path: Path) -> bool:
        return _probe_path_writeable(path)

    def _is_file_locked(self, path: Path) -> bool:
        return _is_file_locked(path)

    def _find_files_by_content(self, directory: Path, text_pattern: str, recursive: bool) -> list[Path]:
        return _find_files_by_content(directory, text_pattern, recursive)