"""
✅ Public Utility Functions (Wrapper around FileSystemService)
"""
from quack_core.core.fs.api.public.checksums import compute_checksum
from quack_core.core.fs.api.public.disk import get_disk_usage, is_path_writeable
from quack_core.core.fs.api.public.file_info import (
    get_file_size_str, get_file_timestamp, get_file_type, get_mime_type, is_file_locked
)
from quack_core.core.fs.api.public.file_ops import (
    atomic_write, ensure_directory, find_files_by_content, get_unique_filename
)
from quack_core.core.fs.api.public.path_ops import (
    expand_user_vars, is_same_file, is_subdirectory, normalize_path, split_path
)
from quack_core.core.fs.api.public.path_utils import (
    extract_path_from_result, extract_path_str, safe_path_str
)
from quack_core.core.fs.api.public.safe_ops import (
    copy_safely, delete_safely, move_safely
)
from quack_core.core.fs.api.public.temp import (
    create_temp_directory, create_temp_file
)
from quack_core.core.fs.api.public.coerce import (
    coerce_path, coerce_path_str, coerce_path_result
)

__all__ = [
    "compute_checksum", "get_disk_usage", "is_path_writeable", "get_file_type", "get_file_size_str",
    "get_file_timestamp", "get_mime_type", "is_file_locked", "atomic_write", "ensure_directory",
    "find_files_by_content", "get_unique_filename", "expand_user_vars", "is_same_file", "is_subdirectory",
    "normalize_path", "split_path", "copy_safely", "delete_safely", "move_safely",
    "create_temp_directory", "create_temp_file", "extract_path_from_result", "extract_path_str",
    "safe_path_str", "coerce_path", "coerce_path_str", "coerce_path_result"
]