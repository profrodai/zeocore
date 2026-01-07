# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/logging/__init__.py
# module: quack_core.core.logging.__init__
# role: module
# neighbors: config.py, formatter.py, logger.py
# exports: get_logger, configure_logger, LOG_LEVELS, LogLevel
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Centralized logging module for quack_core.

This package provides a standardized approach to logging throughout quack_core.
It exposes a functional configuration API and a standardized logger getter.
"""

from .config import LOG_LEVELS, LogLevel, configure_logger
from .logger import get_logger

__all__ = ["get_logger", "configure_logger", "LOG_LEVELS", "LogLevel"]
