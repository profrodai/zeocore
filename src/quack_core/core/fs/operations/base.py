# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/operations/base.py
# module: quack_core.core.fs.operations.base
# role: operations
# neighbors: __init__.py, core.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# exports: FileSystemOperations
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

from pathlib import Path
from typing import Any

from quack_core.core.fs.operations.file_info import FileInfoOperationsMixin
from quack_core.core.fs.operations.write_ops import WriteOperationsMixin
from quack_core.core.fs.operations.read_ops import ReadOperationsMixin
from quack_core.core.fs.operations.directory_ops import DirectoryOperationsMixin
from quack_core.core.fs.operations.find_ops import FindOperationsMixin
from quack_core.core.fs.operations.path_ops import PathOperationsMixin
from quack_core.core.fs.operations.serialization_ops import SerializationOperationsMixin
from quack_core.core.fs.operations.utility_ops import UtilityOperationsMixin
from quack_core.core.fs.operations.core import _resolve_path, _initialize_mime_types
# Note: No logger in operations layer

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