# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/logging/logger.py
# module: quack_core.core.logging.logger
# role: module
# neighbors: __init__.py, config.py, formatter.py
# exports: get_logger
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===



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
