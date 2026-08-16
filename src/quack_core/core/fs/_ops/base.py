# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/base.py
# === QV-LLM:END ===

from quack_core.core.fs._ops.core import _initialize_mime_types
from quack_core.core.fs._ops.directory_ops import DirectoryOperationsMixin
from quack_core.core.fs._ops.file_info import FileInfoOperationsMixin
from quack_core.core.fs._ops.find_ops import FindOperationsMixin
from quack_core.core.fs._ops.path_ops import PathOperationsMixin
from quack_core.core.fs._ops.read_ops import ReadOperationsMixin
from quack_core.core.fs._ops.serialization_ops import SerializationOperationsMixin
from quack_core.core.fs._ops.utility_ops import UtilityOperationsMixin
from quack_core.core.fs._ops.write_ops import WriteOperationsMixin


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
    def __init__(self) -> None:
        _initialize_mime_types()
