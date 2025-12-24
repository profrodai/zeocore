# quack-core/src/quack_core/config/tooling/logger.py
"""
Logging setup utilities for QuackTools.

This module provides utilities for setting up consistent logging
across different QuackTools, leveraging quack-core's enhanced logging functionality.
"""

import atexit
import logging
from typing import Any

from quack_core.fs.service import standalone
from quack_core.logging import LOG_LEVELS, LogLevel, configure_logger

# Track file handlers for cleanup during exit
_file_handlers = []


def setup_tool_logging(tool_name: str, log_level: str = "INFO") -> None:
    """
    Set up logging for a QuackTool.

    This sets up a tool-specific logger with console and file output,
    leveraging quack-core's enhanced logging capabilities including
    Teaching Mode support. It also ensures log files are properly
    cleaned up during tests.

    Args:
        tool_name: The tool name, e.g. 'quackmetadata'
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    fs = standalone

    # Normalize log level
    level_name = log_level.upper()
    try:
        level = LOG_LEVELS[LogLevel(level_name)]
    except (ValueError, KeyError):
        level = logging.INFO

    # Prepare log directory and file path
    logs_dir = fs.normalize_path("./logs")
    fs.create_directory(logs_dir, exist_ok=True)
    log_file = fs.join_path(logs_dir, f"{tool_name}.log")

    # Configure the tool's logger using quack-core's configure_logger
    logger = configure_logger(
        name=tool_name,
        level=level,
        log_file=str(log_file),
        teaching_to_stdout=True,
    )

    # Keep track of file handlers for cleanup
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            _file_handlers.append(handler)

    @atexit.register
    def _cleanup_handlers() -> None:
        """Remove and close file handlers at exit time."""
        for h in _file_handlers:
            h.close()
            if h in logger.handlers:
                logger.removeHandler(h)


def get_logger(tool_name: str) -> logging.Logger:
    """
    Get a named logger for the given tool.

    This is a thin wrapper around quack-core.logging.get_logger
    that ensures the tool's logger is properly configured.

    Args:
        tool_name: The tool name, e.g. 'quackmetadata'

    Returns:
        A Logger instance configured for the tool with quack-core enhancements
    """
    from quack_core.logging import get_logger as core_get_logger
    return core_get_logger(tool_name)


def log_teaching(logger: Any, message: str, level: str = "INFO") -> None:
    """
    Log a Teaching Mode message for the tool.

    This is a convenience wrapper around quack-core.logging.config.log_teaching.

    Args:
        logger: The logger instance
        message: The message to log
        level: The log level to use (default: INFO)
    """
    from quack_core.logging.config import log_teaching as core_log_teaching
    core_log_teaching(logger, message, level)
