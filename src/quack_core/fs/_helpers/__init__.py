# quack-core/src/quack-core/fs/_helpers/__init__.py

"""
🛑 INTERNAL USE ONLY — DO NOT IMPORT FROM HERE

This package contains low-level filesystem _helpers. They are:
- NOT covered by semver
- NOT safe for public use
- MAY be refactored or removed without warning

Use `fs.service` or `fs.api.public` instead.
"""

# Explicitly define an empty __all__ to prevent people from importing
# anything from here
__all__ = []

# Imports for internal use only - all prefixed with underscore
from quack_core.fs._helpers.checksums import _compute_checksum
from quack_core.fs._helpers.common import _get_extension, _normalize_path
from quack_core.fs._helpers.comparison import _is_same_file, _is_subdirectory
from quack_core.fs._helpers.disk import _get_disk_usage, _is_path_writeable
from quack_core.fs._helpers.file_info import (
    _get_file_size_str,
    _get_file_timestamp,
    _get_file_type,
    _get_mime_type,
    _is_file_locked,
)
from quack_core.fs._helpers.file_ops import (
    _atomic_write,
    _ensure_directory,
    _find_files_by_content,
    _get_unique_filename,
)
from quack_core.fs._helpers.path_ops import _expand_user_vars, _split_path
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.fs._helpers.safe_ops import _safe_copy, _safe_delete, _safe_move
from quack_core.fs._helpers.temp import _create_temp_directory, _create_temp_file
