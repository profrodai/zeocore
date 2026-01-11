# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/base.py
# module: quack_core.core.fs._ops.base
# role: _ops
# neighbors: __init__.py, core.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# exports: FileSystemOperations
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

from pathlib import Path
from typing import Any

from quack_core.core.fs._ops.file_info import FileInfoOperationsMixin
from quack_core.core.fs._ops.write_ops import WriteOperationsMixin
from quack_core.core.fs._ops.read_ops import ReadOperationsMixin
from quack_core.core.fs._ops.directory_ops import DirectoryOperationsMixin
from quack_core.core.fs._ops.find_ops import FindOperationsMixin
from quack_core.core.fs._ops.path_ops import PathOperationsMixin
from quack_core.core.fs._ops.serialization_ops import SerializationOperationsMixin
from quack_core.core.fs._ops.utility_ops import UtilityOperationsMixin
from quack_core.core.fs._ops.core import _resolve_path, _initialize_mime_types

class FileSystemOperations(
    ReadOperationsMixin,
    WriteOperationsMixin,
    FileInfoOperationsMixin,
    DirectoryOperationsMixin,
    FindOperationsMixin,
    SerializationOperationsMixin,
    PathOperationsMixin,
    UtilityOperationsMixin,
):
    def __init__(self, base_dir: Any = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        _initialize_mime_types()

    def _resolve_path(self, path: str | Path) -> Path:
        return _resolve_path(self.base_dir, path)