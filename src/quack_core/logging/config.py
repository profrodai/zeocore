# quack-core/src/quack_core/logging/config.py
"""
Logger configuration for quack_core.

This module handles the setup and configuration of loggers,
including environment-based configuration and file output options.
Note: Filesystem-related _operations are imported lazily to avoid circular dependencies.
"""

import logging
import os
import sys
from enum import Enum
from typing import Any

# Import our custom formatter
from .formatter import TeachingAwareFormatter


# Define log levels enum for easy reference
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Mapping from string names to logging module constants
LOG_LEVELS = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL,
}


def get_log_level() -> int:
    """
    Get the log level from the environment variable or default to INFO.

    Returns:
        The log level as a logging module constant.
    """
    env_level = os.environ.get("QUACKCORE_LOG_LEVEL", "INFO").upper()
    log_level = logging.INFO
    try:
        log_level = LOG_LEVELS[LogLevel(env_level)]
    except (ValueError, KeyError):
        # If env_level is invalid, default to INFO
        pass
    return log_level


def configure_logger(
    name: str | None = None,
    level: int | None = None,
    log_file: str | None = None,
    teaching_to_stdout: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger with the specified name.

    This function sets up handlers only once per logger instance and supports
    multiple output destinations (console and file). Filesystem _operations are
    performed via quack_core.fs.service, imported only inside this function.

    Args:
        name: The name for the logger, typically __name__.
        level: The logging level (if None, determined by environment).
        log_file: Optional log file path.
        teaching_to_stdout: If True, teaching messages go to stdout; otherwise stderr.

    Returns:
        A configured logger.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger_level = level if level is not None else get_log_level()
        logger.setLevel(logger_level)

        # Console handler with TeachingAwareFormatter
        console_handler = logging.StreamHandler(
            sys.stdout if teaching_to_stdout else sys.stderr
        )
        console_handler.setFormatter(TeachingAwareFormatter())
        logger.addHandler(console_handler)

        # File handler (if log_file provided)
        if log_file:
            # Lazy import of filesystem service to avoid circular dependency.
            from quack_core.fs.service import standalone

            # Resolve parent directory for the log file.
            parent_dir = standalone.join_path(*standalone.split_path(log_file)[:-1])
            standalone.create_directory(parent_dir, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(TeachingAwareFormatter(color_enabled=False))
            logger.addHandler(file_handler)

        # Prevent propagation to avoid duplicate logging.
        logger.propagate = False

    return logger


def log_teaching(logger: Any, message: str, level: str = "INFO") -> None:
    """
    Log a Teaching Mode message with appropriate formatting.

    Args:
        logger: The logger instance.
        message: The message to log.
        level: The log level to use.
    """
    log_method = getattr(logger, level.lower())
    log_method(f"[Teaching Mode] {message}")
