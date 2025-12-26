# quack-core/src/quack_core/interfaces/cli/utils/error.py
"""
Error handling utilities for CLI applications.

This module provides functions for handling and formatting errors
in CLI applications, with proper output formatting and consistent
error messaging.
"""

import os
import sys
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from quack_core.lib.errors import QuackError

T = TypeVar("T")  # Generic type for flexible typing


def format_cli_error(error: Exception) -> str:
    """
    Format an error for CLI display.

    Args:
        error: The exception to format

    Returns:
        Formatted error message suitable for CLI output
    """
    if isinstance(error, QuackError):
        message = str(error)
        parts = [message]

        if hasattr(error, "context") and error.context:
            parts.append("\nContext:")
            for key, value in error.context.items():
                parts.append(f"  {key}: {value}")

        if (
            hasattr(error, "original_error")
            and error.original_error
            and error.original_error is not error
        ):
            parts.append(f"\nOriginal error: {error.original_error}")

        return "\n".join(parts)
    else:
        return str(error)


# Import the print_error function from our CLI formatting module.
# (This import is left as-is because it is not related to file paths.)
from quack_core.interfaces.cli.utils.formatting import print_error as _print_error


def handle_errors(
    error_types: type[Exception] | tuple[type[Exception], ...] = Exception,
    title: str | None = None,
    show_traceback: bool = False,
    exit_code: int | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """
    Decorator to handle errors in a function.

    Args:
        error_types: The exception type(s) to catch
        title: An optional title for the error panel
        show_traceback: Whether to show the traceback
        exit_code: If provided, exit with this code after handling the error

    Returns:
        A decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        def wrapper(*args: object, **kwargs: object) -> T | None:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                func_title = title or f"Error in {func.__name__}"
                _print_error(f"{func_title}: {format_cli_error(e)}")

                if show_traceback:
                    import traceback

                    traceback.print_exc()

                if exit_code is not None:
                    sys.exit(exit_code)
                return None

        return wrapper

    return decorator


def ensure_single_instance(app_name: str) -> bool:
    """
    Ensure only one instance of a CLI application is running.

    This is useful for daemons or long-running services that should
    not have multiple instances running concurrently.

    Args:
        app_name: Name of the application

    Returns:
        True if this is the only instance, False otherwise
    """
    import atexit
    import socket
    from tempfile import gettempdir

    temp_dir = gettempdir()
    # Construct the lock file as a string path using os.path.join
    lock_path = os.path.join(temp_dir, f"{app_name}.lock")
    # Derive a port number based on the app name
    port = sum(ord(c) for c in app_name) % 10000 + 10000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.bind(("127.0.0.1", port))
        with open(lock_path, "w") as f:
            f.write(str(os.getpid()))

        def cleanup() -> None:
            sock.close()
            try:
                os.remove(lock_path)
            except (FileNotFoundError, PermissionError, OSError):
                pass

        atexit.register(cleanup)
        return True

    except OSError:
        return False


def _get_current_datetime() -> datetime:
    """
    Get the current datetime.

    Returns:
        Current datetime.
    """
    return datetime.now()


def get_cli_info() -> dict[str, Any]:
    """
    Get information about the CLI environment.

    Returns:
        Dictionary with CLI environment information.
    """
    import platform

    from quack_core.interfaces.cli.utils.terminal import get_terminal_size
    from quack_core.config.utils import get_env

    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "time": _get_current_datetime().isoformat(),
        "pid": os.getpid(),
        "cwd": os.getcwd(),  # Current working directory as a string
        "environment": get_env(),
    }

    try:
        columns, lines = get_terminal_size()
        info["terminal_size"] = f"{columns}x{lines}"
    except (AttributeError, OSError):
        info["terminal_size"] = "unknown"

    info["username"] = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    info["is_ci"] = bool(
        "CI" in os.environ
        or "GITHUB_ACTIONS" in os.environ
        or "GITLAB_CI" in os.environ
    )

    return info
