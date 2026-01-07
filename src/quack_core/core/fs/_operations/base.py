# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_operations/base.py
# module: quack_core.core.fs._operations.base
# role: module
# neighbors: __init__.py, core.py, directory_ops.py, file_info.py, find_ops.py, path_ops.py (+4 more)
# exports: FileSystemOperations
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from pathlib import Path
from typing import Any

from quack_core.core.fs._operations.file_info import FileInfoOperationsMixin
from quack_core.core.fs._operations.write_ops import WriteOperationsMixin
from quack_core.core.fs._operations.read_ops import ReadOperationsMixin
from quack_core.core.fs._operations.directory_ops import DirectoryOperationsMixin
from quack_core.core.fs._operations.find_ops import FindOperationsMixin
from quack_core.core.fs._operations.path_ops import PathOperationsMixin
from quack_core.core.fs._operations.serialization_ops import SerializationOperationsMixin
from quack_core.core.fs._operations.utility_ops import UtilityOperationsMixin
from quack_core.core.fs._operations.core import _resolve_path, _initialize_mime_types
from quack_core.core.logging import get_logger

logger = get_logger(__name__)

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
        logger.debug(f"FileSystemOperations initialized at {self.base_dir}")

    def _resolve_path(self, path: str | Path) -> Path:
        return _resolve_path(self.base_dir, path)