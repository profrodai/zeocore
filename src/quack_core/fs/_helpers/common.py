# quack-core/src/quack-core/fs/_helpers/common.py
"""
Common utility functions for filesystem _operations.
"""

from pathlib import Path

from quack_core.errors import wrap_io_errors
from quack_core.logging import get_logger

# Initialize module logger
logger = get_logger(__name__)


def _get_extension(path: str | Path) -> str:
    """
    Get the file extension from a path.

    Args:
        path: File path (string or Path)

    Returns:
        File extension without the dot
    """
    # Normalize input to Path object early
    path_obj = Path(path)
    filename = path_obj.name

    # Special case for dotfiles
    if filename.startswith(".") and "." not in filename[1:]:
        return filename[1:]  # Return everything after the first dot for dotfiles

    return path_obj.suffix.lstrip(".")


@wrap_io_errors
def _normalize_path(path: str | Path) -> Path:
    """
    Normalize a path for cross-platform compatibility.

    This does not check if the path exists.

    Args:
        path: Path to normalize (string or Path)

    Returns:
        Normalized Path object
    """
    # Ensure we're working with a Path object
    path_obj = Path(path).expanduser()

    # If path is already absolute, no need for getcwd() which might fail
    if path_obj.is_absolute():
        return path_obj

    try:
        # Try to make it absolute or resolve it
        if not path_obj.exists():
            return path_obj.absolute()
        return path_obj.resolve()
    except (FileNotFoundError, OSError) as e:
        # If any OS error occurs (including getcwd() failing),
        # just return the path as is, with a warning
        logger.warning(f"Could not normalize path '{path}': {str(e)}")
        return path_obj
