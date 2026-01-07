# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/utils/__init__.py
# module: quack_core.core.fs.utils.__init__
# role: utils
# exports: atomic_write, compute_checksum, copy_safely, create_temp_directory, create_temp_file, delete_safely, ensure_directory, expand_user_vars (+17 more)
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/utils/__init__.py
"""
Utility functions for the filesystem module.

This module provides high-level utility functions that build upon
the basic _operations provided by the FileSystemService.

Note: This is a legacy name preserved for backward compatibility.
For new code, prefer using `quack_core.fs.api.public` instead.
"""

from quack_core.fs.api import (
    atomic_write,
    compute_checksum,
    copy_safely,
    create_temp_directory,
    create_temp_file,
    delete_safely,
    ensure_directory,
    expand_user_vars,
    extract_path_from_result,
    extract_path_str,
    find_files_by_content,
    get_disk_usage,
    get_file_size_str,
    get_file_timestamp,
    get_file_type,
    get_mime_type,
    get_unique_filename,
    is_file_locked,
    is_path_writeable,
    is_same_file,
    is_subdirectory,
    move_safely,
    normalize_path,
    safe_path_str,
    split_path,
)

__all__ = [
    # Re-export everything from api
    "atomic_write",
    "compute_checksum",
    "copy_safely",
    "create_temp_directory",
    "create_temp_file",
    "delete_safely",
    "ensure_directory",
    "expand_user_vars",
    "find_files_by_content",
    "get_disk_usage",
    "get_file_size_str",
    "get_file_timestamp",
    "get_file_type",
    "get_mime_type",
    "get_unique_filename",
    "is_file_locked",
    "is_path_writeable",
    "is_same_file",
    "is_subdirectory",
    "move_safely",
    "normalize_path",
    "split_path",
    "extract_path_from_result",
    "safe_path_str",
    "extract_path_str",
]
