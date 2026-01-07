# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_helpers/disk.py
# module: quack_core.core.fs._helpers.disk
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, file_info.py, file_ops.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/_helpers/disk.py
"""
Utility functions for disk _operations.
"""

import os
import shutil
from typing import Any

from quack_core.errors import QuackIOError

# Import path normalization helper
from quack_core.fs._helpers.path_utils import _normalize_path_param
from quack_core.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


def _get_disk_usage(path: Any) -> dict[str, int]:
    """
    Get disk usage information for the given path.

    Args:
        path: Path to get disk usage for (can be str, Path, or any object with 'data' attribute)

    Returns:
        Dictionary with total, used, and free space in bytes

    Raises:
        QuackIOError: If disk usage cannot be determined.
    """
    # Normalize to Path object using the dedicated helper
    path_obj = _normalize_path_param(path)

    try:
        total, used, free = shutil.disk_usage(str(path_obj))
        logger.debug(
            f"Disk usage for {path_obj}: total={total}, used={used}, free={free}")
        return {"total": total, "used": used, "free": free}
    except Exception as e:
        logger.error(f"Failed to get disk usage for {path_obj}: {e}")
        raise QuackIOError(
            f"Error getting disk usage for {path_obj}: {e}", str(path_obj)
        ) from e


def _is_path_writeable(path: Any) -> bool:
    """
    Check if a path is writeable.

    Args:
        path: Path to check (can be str, Path, or any object with 'data' attribute)

    Returns:
        True if the path is writeable
    """
    # Normalize to Path object using the dedicated helper
    path_obj = _normalize_path_param(path)

    if not path_obj.exists():
        try:
            if path_obj.suffix:
                with open(path_obj, "w") as _:
                    pass
                path_obj.unlink()  # Clean up
            else:
                path_obj.mkdir(parents=True)
                path_obj.rmdir()  # Clean up
            logger.debug(
                f"Path {path_obj} is writeable (created and removed test objects)")
            return True
        except Exception as e:
            logger.debug(f"Path {path_obj} is not writeable: {e}")
            return False

    if path_obj.is_file():
        result = os.access(path_obj, os.W_OK)
        logger.debug(f"File {path_obj} writeable check result: {result}")
        return result

    if path_obj.is_dir():
        try:
            test_file = path_obj / f"test_write_{os.getpid()}.tmp"
            with open(test_file, "w") as _:
                pass
            test_file.unlink()  # Clean up
            logger.debug(
                f"Directory {path_obj} is writeable (created and removed test file)"
            )
            return True
        except Exception as e:
            logger.debug(f"Directory {path_obj} is not writeable: {e}")
            return False

    return False
