# quack-core/src/quack_core/interfaces/cli/utils/terminal.py
"""
Terminal utilities for CLI applications.

This module provides functions for working with terminal capabilities,
such as getting terminal size and checking for color support.
"""

import os
import sys


def get_terminal_size() -> tuple[int, int]:
    """
    Get the terminal size.

    Returns:
        A tuple of (columns, lines)
    """
    try:
        import shutil

        terminal_size = shutil.get_terminal_size((80, 24))
        return terminal_size.columns, terminal_size.lines
    except (ImportError, OSError):
        return 80, 24


def supports_color() -> bool:
    """
    Check if the terminal supports color output.

    Returns:
        True if color is supported, False otherwise
    """
    # Return False if NO_COLOR env var is set (https://no-color.org/)
    if os.environ.get("NO_COLOR") is not None:
        return False

    # Return False if --no-color flag was used
    if "--no-color" in sys.argv:
        return False

    # Check if stdout is a TTY
    is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    # If running in GitHub Actions, colors are supported
    in_github_actions = "GITHUB_ACTIONS" in os.environ

    # If running in CI that supports color, allow it
    in_ci_with_color = (
        "CI" in os.environ and os.environ.get("CI_FORCE_COLORS", "0") == "1"
    )

    return is_tty or in_github_actions or in_ci_with_color


def truncate_text(text: str, max_length: int, indicator: str = "...") -> str:
    """
    Truncate text to a maximum length with an indicator.

    Args:
        text: Text to truncate
        max_length: Maximum length
        indicator: String to append to truncated text

    Returns:
        Truncated text
    """
    # Handle case where indicator is longer than max_length
    if len(indicator) >= max_length:
        return indicator[:max_length]

    if len(text) <= max_length:
        return text

    return text[: max_length - len(indicator)] + indicator
