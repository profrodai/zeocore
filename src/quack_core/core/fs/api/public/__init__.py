# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/__init__.py
# module: quack_core.core.fs.api.public.__init__
# role: api
# neighbors: checksums.py, coerce.py, disk.py, file_info.py, file_ops.py, path_ops.py (+3 more)
# exports: compute_checksum, get_disk_usage, is_path_writeable, get_file_type, get_file_size_str, get_file_timestamp, get_mime_type, is_file_locked (+19 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
✅ Public Utility Functions (Safe for QuackTools and DuckTyper)

These are stable, documented, and error-handled _internal for working with the filesystem.
If you're building with `quack_core.core.fs.service`, use these functions directly.
"""

from quack_core.core.fs.api.public.checksums import compute_checksum
from quack_core.core.fs.api.public.disk import get_disk_usage, is_path_writeable
from quack_core.core.fs.api.public.file_info import (
    get_file_size_str,
    get_file_timestamp,
    get_file_type,
    get_mime_type,
    is_file_locked,
)
from quack_core.core.fs.api.public.file_ops import (
    atomic_write,
    ensure_directory,
    find_files_by_content,
    get_unique_filename,
)
from quack_core.core.fs.api.public.path_ops import (
    expand_user_vars,
    is_same_file,
    is_subdirectory,
    normalize_path,
    split_path,
)
from quack_core.core.fs.api.public.path_utils import (
    extract_path_str,
    safe_path_str,
)
from quack_core.core.fs.api.public.safe_ops import (
    copy_safely,
    delete_safely,
    move_safely,
)
from quack_core.core.fs.api.public.temp import (
    create_temp_directory,
    create_temp_file,
)
from quack_core.core.fs.api.public.coerce import (
    coerce_path,
    coerce_path_str,
    coerce_path_result,
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
    "extract_path_str",
    "safe_path_str",
    # Coercion
    "coerce_path",
    "coerce_path_str",
    "coerce_path_result",
]