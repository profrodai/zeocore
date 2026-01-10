from quack_core.core.fs.service.base import FileSystemService as BaseFileSystemService
from quack_core.core.fs.service.directory_operations import DirectoryOperationsMixin
from quack_core.core.fs.service.file_operations import FileOperationsMixin
from quack_core.core.fs.service.path_operations import PathOperationsMixin
from quack_core.core.fs.service.utility_operations import UtilityOperationsMixin
from quack_core.core.fs.service.structured_data import StructuredDataMixin
from quack_core.core.fs.service.path_validation import PathValidationMixin

class FileSystemService(
    BaseFileSystemService,
    FileOperationsMixin,
    DirectoryOperationsMixin,
    StructuredDataMixin,
    PathOperationsMixin,
    PathValidationMixin,
    UtilityOperationsMixin,
):
    pass