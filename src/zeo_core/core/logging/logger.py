
"""
Defines helper functions for obtaining loggers.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    This returns a standard Python logger.
    Note: To ensure handlers are attached, `configure_logger` must be called
    at application startup (bootstrap).

    Args:
        name: The name for the logger, typically __name__

    Returns:
        A logging.Logger instance.
    """
    return logging.getLogger(name)
