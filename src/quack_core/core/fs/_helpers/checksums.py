# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_helpers/checksums.py
# module: quack_core.core.fs._helpers.checksums
# role: module
# neighbors: __init__.py, common.py, comparison.py, disk.py, file_info.py, file_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_helpers/checksums.py
"""
Utility functions for file checksums.
"""

import hashlib
from typing import Any

from quack_core.errors import QuackFileNotFoundError, QuackIOError, wrap_io_errors

# Import path normalization helper
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


@wrap_io_errors
def _compute_checksum(path: Any, algorithm: str = "sha256") -> str:
    """
    Compute checksum of a file.

    Args:
        path: Path to the file (can be str, Path, or any object with 'data' attribute)
        algorithm: Hash algorithm to use

    Returns:
        Hexadecimal checksum string

    Raises:
        QuackFileNotFoundError: If file doesn't exist
        QuackIOError: For other IO related issues
    """
    # Normalize using the dedicated helper
    path_obj = _normalize_path_param(path)

    if not path_obj.exists():
        logger.error(f"File not found when computing checksum: {path_obj}")
        raise QuackFileNotFoundError(str(path_obj))
    if not path_obj.is_file():
        logger.error(f"Not a file when computing checksum: {path_obj}")
        raise QuackIOError("Not a file", str(path_obj))

    try:
        hash_obj = getattr(hashlib, algorithm)()
        logger.debug(f"Computing {algorithm} checksum for {path_obj}")

        with open(path_obj, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        checksum = hash_obj.hexdigest()
        logger.debug(f"Checksum for {path_obj}: {checksum}")
        return checksum
    except Exception as e:
        logger.error(f"Failed to compute checksum for {path_obj}: {e}")
        raise QuackIOError(
            f"Failed to compute checksum for {path_obj}: {str(e)}",
            str(path_obj),
            original_error=e,
        ) from e
