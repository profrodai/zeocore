from pathlib import Path
from typing import Any

from quack_core.fs.operations.file_info import FileInfoOperationsMixin
from quack_core.fs.operations.write_ops import WriteOperationsMixin
from quack_core.fs.operations.read_ops import ReadOperationsMixin
from quack_core.fs.operations.directory_ops import DirectoryOperationsMixin
from quack_core.fs.operations.find_ops import FindOperationsMixin
from quack_core.fs.operations.path_ops import PathOperationsMixin
from quack_core.fs.operations.serialization_ops import SerializationOperationsMixin
from quack_core.fs.operations.utility_ops import UtilityOperationsMixin
from quack_core.fs.operations.core import _resolve_path, _initialize_mime_types
from quack_core.lib.logging import get_logger

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