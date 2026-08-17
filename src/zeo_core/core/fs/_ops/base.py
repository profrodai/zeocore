from zeo_core.core.fs._ops.core import _initialize_mime_types
from zeo_core.core.fs._ops.directory_ops import DirectoryOperationsMixin
from zeo_core.core.fs._ops.file_info import FileInfoOperationsMixin
from zeo_core.core.fs._ops.find_ops import FindOperationsMixin
from zeo_core.core.fs._ops.path_ops import PathOperationsMixin
from zeo_core.core.fs._ops.read_ops import ReadOperationsMixin
from zeo_core.core.fs._ops.serialization_ops import SerializationOperationsMixin
from zeo_core.core.fs._ops.utility_ops import UtilityOperationsMixin
from zeo_core.core.fs._ops.write_ops import WriteOperationsMixin


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
