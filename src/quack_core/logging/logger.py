# quack-core/src/quack-core/logging/logger.py
"""
Defines helper functions for obtaining loggers.
"""

from logging import Logger  # Standard logger type for type annotations

from .config import configure_logger


def get_logger(name: str) -> Logger:
    """
    Get a configured logger for a specific module.

    Args:
        name: The name for the logger, typically __name__

    Returns:
        A logger configured using quack-core's settings.
    """
    return configure_logger(name)
