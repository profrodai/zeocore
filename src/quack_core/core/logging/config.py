# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/logging/config.py
# module: quack_core.core.logging.config
# role: module
# neighbors: __init__.py, formatter.py, logger.py
# exports: LogLevel, configure_logger, log_teaching
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

"""
Logger configuration for quack_core.

This module handles the setup and configuration of loggers.
It supports filesystem operations via lazy imports to avoid circular dependencies.
"""

import logging
import os
import sys
from enum import Enum

from .formatter import TeachingAwareFormatter, TEACHING_EXTRA_KEY


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


LOG_LEVELS = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL,
}


def _get_default_level() -> int:
    """
    Get the default log level from environment variable.

    This acts as a fallback mechanism. Ring C (application layer) should preferably
    pass an explicit configuration object.
    """
    env_level = os.environ.get("QUACKCORE_LOG_LEVEL", "INFO").upper()
    try:
        return LOG_LEVELS[LogLevel(env_level)]
    except (ValueError, KeyError):
        return logging.INFO


def configure_logger(
        name: str,
        level: int | None = None,
        log_file: str | None = None,
        teaching_to_stdout: bool = True,
        propagate: bool = False,
        force: bool = False,
) -> logging.Logger:
    """
    Configure and return a logger with the specified name.

    Args:
        name: The logger name.
        level: Logging level (defaults to env var if None).
        log_file: Path to log file.
        teaching_to_stdout: If True, teaching messages go to stdout.
        propagate: Whether to propagate messages to the root logger.
        force: If True, existing handlers are removed and closed before configuration.
               If False, configuration is skipped if handlers already exist.

    Returns:
        The configured logger instance.
    """
    logger = logging.getLogger(name)

    # Set level (prioritize arg, then env/default)
    final_level = level if level is not None else _get_default_level()
    logger.setLevel(final_level)
    logger.propagate = propagate

    # Handle existing configuration
    if logger.handlers:
        if not force:
            return logger

        # Safe cleanup: remove and close all handlers to avoid resource leaks
        for h in list(logger.handlers):
            logger.removeHandler(h)
            try:
                h.close()
            except Exception:
                # Swallow errors during closure to ensure we proceed with config
                pass

    # Console handler
    stream = sys.stdout if teaching_to_stdout else sys.stderr
    console_handler = logging.StreamHandler(stream)
    console_handler.setFormatter(TeachingAwareFormatter())
    logger.addHandler(console_handler)

    # File handler (if requested)
    if log_file:
        # Lazy import of filesystem service to avoid circular dependency
        from quack_core.core.fs.service import standalone

        # Resolve parent directory safely
        parts = standalone.split_path(log_file)
        parent_parts = parts[:-1]

        # Only attempt to create directory if a parent path exists
        if parent_parts:
            parent_dir = standalone.join_path(*parent_parts)
            standalone.create_directory(parent_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(TeachingAwareFormatter(color_enabled=False))
        logger.addHandler(file_handler)

    return logger


def log_teaching(logger: logging.Logger, message: str, level: str = "INFO") -> None:
    """
    Log a Teaching Mode message with appropriate formatting and metadata.

    Args:
        logger: The logger instance to use.
        message: The teaching message content.
        level: Log level (default: INFO).
    """
    log_method = getattr(logger, level.lower(), logger.info)

    # We include the prefix for standard logs, but add the structured key
    # so the formatter can detect it reliably without string parsing.
    log_method(f"[Teaching Mode] {message}", extra={TEACHING_EXTRA_KEY: True})