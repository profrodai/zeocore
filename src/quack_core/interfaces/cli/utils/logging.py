# quack-core/src/quack_core/interfaces/cli/utils/logging.py
"""
Logging utilities for CLI applications.

This module provides functions for setting up logging in CLI applications,
with flexible configuration options and consistent output formatting.
"""

import atexit
import logging
import os
from typing import Protocol, TypeVar


from quack_core.config.models import QuackConfig
from quack_core.interfaces.cli.utils.options import LogLevel

T = TypeVar("T")  # Generic type for flexible typing


class LoggerFactory(Protocol):
    """Protocol for logger factory functions."""

    def __call__(self, name: str) -> logging.Logger:
        """
        Create or get a logger with the given name.

        Args:
            name: The name of the logger

        Returns:
            A configured logger instance
        """
        ...


def _determine_effective_level(
    cli_log_level: LogLevel | None,
    cli_debug: bool,
    cli_quiet: bool,
    cfg: QuackConfig | None,
) -> LogLevel:
    """
    Determine the effective logging level based on various inputs.

    Args:
        cli_log_level: Optional logging level override from CLI
        cli_debug: True if debug flag is set
        cli_quiet: True if quiet flag is set
        cfg: Optional configuration with logging settings

    Returns:
        The effective log level as a string
    """
    if cli_debug:
        return "DEBUG"
    if cli_quiet:
        return "ERROR"
    if cli_log_level is not None:
        return cli_log_level
    if cfg and cfg.logging.level:
        config_level = cfg.logging.level.upper()
        if config_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            return config_level  # type: ignore
    return "INFO"


# Keep track of file handlers we've added
_file_handlers: list[logging.FileHandler] = []


def _add_file_handler(
    root_logger: logging.Logger,
    cfg: QuackConfig,
    level_value: int,
    console_formatter: logging.Formatter | None = None,
) -> None:
    """
    Add a file handler to the root logger if a log file is specified in the config.

    Args:
        root_logger: The root logger to configure
        cfg: The configuration containing logging settings
        level_value: The numeric logging level
        console_formatter: Optional formatter to use for consistency with console output
    """
    # Import create_directory from the filesystem service to handle directory creation.
    from quack_core.fs.service import create_directory

    try:
        # Expect the logging file setting to be provided as a string.
        log_file = cfg.logging.file
        if not log_file:
            return

        # Obtain the directory of the log file using os.path (all as strings)
        log_dir = os.path.dirname(log_file)

        # Create the log directory using the filesystem service
        result = create_directory(log_dir, exist_ok=True)

        # If directory creation failed, warn and return
        if not result.success:
            root_logger.warning(f"Failed to create log directory: {result.error}")
            return

        root_logger.debug(f"Log directory created: {log_dir}")

        # Create the file handler using the log file string
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level_value)

        if console_formatter:
            file_handler.setFormatter(console_formatter)
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)

        root_logger.addHandler(file_handler)
        root_logger.debug(f"Log file configured: {log_file}")

        # Keep track of file handlers for cleanup
        _file_handlers.append(file_handler)
    except Exception as e:
        root_logger.warning(f"Failed to set up log file: {e}")


@atexit.register
def _cleanup_file_handlers() -> None:
    """Close all file handlers on exit to prevent resource warnings."""
    for handler in _file_handlers:
        try:
            handler.close()
        except Exception:
            pass
    _file_handlers.clear()


def setup_logging(
    log_level: LogLevel | None = None,
    debug: bool = False,
    quiet: bool = False,
    config: QuackConfig | None = None,
    logger_name: str = "quack",
) -> tuple[logging.Logger, LoggerFactory]:
    """
    Set up logging for CLI applications.

    This function configures logging based on CLI flags and configuration settings,
    ensuring consistent logging behavior across all QuackVerse tools.

    Args:
        log_level: Optional logging level (overrides config and other flags)
        debug: Whether debug mode is enabled (sets log level to DEBUG)
        quiet: Whether to suppress non-error output (sets log level to ERROR)
        config: Optional configuration to use for logging setup
        logger_name: Base name for the logger

    Returns:
        A tuple containing:
        - The root logger instance
        - A logger factory function to create named loggers
    """
    effective_level: LogLevel = _determine_effective_level(
        log_level, debug, quiet, config
    )
    try:
        level_value = getattr(logging, effective_level)
    except (AttributeError, TypeError):
        level_value = logging.INFO

    root_logger = logging.getLogger(logger_name)
    root_logger.propagate = False
    root_logger.setLevel(level_value)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level_value)

    if effective_level == "DEBUG":
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        formatter = logging.Formatter("%(levelname)s: %(message)s")

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if config and config.logging.file:
        _add_file_handler(root_logger, config, level_value, formatter)

    def get_logger(name: str) -> logging.Logger:
        """Create or get a named logger with the configured settings."""
        logger_obj = logging.getLogger(f"{logger_name}.{name}")
        logger_obj.setLevel(root_logger.level)
        return logger_obj

    return root_logger, get_logger
