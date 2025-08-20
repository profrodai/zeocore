# quack-core/src/quack-core/fs/api/public/__init__.py
"""
✅ Public Utility Functions (Safe for QuackTools and DuckTyper)

These are stable, documented, and error-handled _helpers for working with the filesystem.
If you're building with `quack-core.fs.service`, use these functions directly.
"""

from quackcore.fs.api.public.checksums import compute_checksum
from quackcore.fs.api.public.disk import get_disk_usage, is_path_writeable
from quackcore.fs.api.public.file_info import (
    get_file_size_str,
    get_file_timestamp,
    get_file_type,
    get_mime_type,
    is_file_locked,
)
from quackcore.fs.api.public.file_ops import (
    atomic_write,
    ensure_directory,
    find_files_by_content,
    get_unique_filename,
)
from quackcore.fs.api.public.path_ops import (
    expand_user_vars,
    is_same_file,
    is_subdirectory,
    normalize_path,
    split_path,
)
from quackcore.fs.api.public.path_utils import (
    extract_path_from_result,
    extract_path_str,
    safe_path_str,
)
from quackcore.fs.api.public.safe_ops import (
    copy_safely,
    delete_safely,
    move_safely,
)
from quackcore.fs.api.public.temp import (
    create_temp_directory,
    create_temp_file,
)

__all__ = [
    # Checksums
    "compute_checksum",
    # Disk _operations
    "get_disk_usage",
    "is_path_writeable",
    # File information
    "get_file_type",
    "get_file_size_str",
    "get_file_timestamp",
    "get_mime_type",
    "is_file_locked",
    # File _operations
    "atomic_write",
    "ensure_directory",
    "find_files_by_content",
    "get_unique_filename",
    # Path _operations
    "expand_user_vars",
    "is_same_file",
    "is_subdirectory",
    "normalize_path",
    "split_path",
    # Safe _operations
    "copy_safely",
    "delete_safely",
    "move_safely",
    # Temporary files and directories
    "create_temp_directory",
    "create_temp_file",
    # Path utils
    "extract_path_from_result",
    "extract_path_str",
    "safe_path_str",
]
