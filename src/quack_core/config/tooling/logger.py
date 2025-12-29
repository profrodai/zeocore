# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/tooling/logger.py
# module: quack_core.config.tooling.logger
# role: module
# neighbors: __init__.py, base.py, loader.py
# exports: setup_tool_logging, get_logger, log_teaching
# git_branch: refactor/toolkitWorkflow
# git_commit: 21647d6
# === QV-LLM:END ===


"""
Logging setup utilities for QuackTools.

This module helps tools configure logging.
It does NOT auto-create directories unless explicitly told to do so via setup.
"""

import atexit
import logging
import os
from typing import Any

from quack_core.lib.logging import LOG_LEVELS, LogLevel, configure_logger

_file_handlers: list[logging.FileHandler] = []


def setup_tool_logging(
        tool_name: str,
        log_dir: str,
        log_level: str = "INFO",
        teaching_to_stdout: bool = False
) -> None:
    """
    Set up logging for a QuackTool with explicit paths.

    Args:
        tool_name: The tool name, e.g. 'quackmetadata'.
        log_dir: The directory where logs should be stored.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        teaching_to_stdout: Whether to output Teaching Mode logs to stdout (opt-in).
    """
    # Normalize log level
    level_name = log_level.upper()
    try:
        level = LOG_LEVELS[LogLevel(level_name)]
    except (ValueError, KeyError):
        level = logging.INFO

    # Create directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"{tool_name}.log")

    # Configure the tool's logger
    logger = configure_logger(
        name=tool_name,
        level=level,
        log_file=str(log_file),
        teaching_to_stdout=teaching_to_stdout,
    )

    # Track handlers for clean exit
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            _file_handlers.append(handler)

    @atexit.register
    def _cleanup_handlers() -> None:
        """Remove and close file handlers at exit time."""
        for h in _file_handlers:
            try:
                h.close()
                if h in logger.handlers:
                    logger.removeHandler(h)
            except Exception:
                pass


def get_logger(tool_name: str) -> logging.Logger:
    """
    Get a named logger for the given tool.
    Wrapper around core logging.
    """
    from quack_core.lib.logging import get_logger as core_get_logger
    return core_get_logger(tool_name)


def log_teaching(logger: Any, message: str, level: str = "INFO") -> None:
    """Log a Teaching Mode message for the tool."""
    from quack_core.lib.logging import log_teaching as core_log_teaching
    core_log_teaching(logger, message, level)
