"""
Centralized logging module for quack_core.

This package provides a standardized approach to logging throughout quack_core.
It exposes a functional configuration API and a standardized logger getter.
"""

from .config import LOG_LEVELS, LogLevel, configure_logger
from .logger import get_logger

__all__ = ["get_logger", "configure_logger", "LOG_LEVELS", "LogLevel"]
