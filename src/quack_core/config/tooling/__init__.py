# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/tooling/__init__.py
# module: quack_core.config.tooling.__init__
# role: module
# neighbors: base.py, loader.py, logger.py
# exports: QuackToolConfigModel, load_tool_config, update_tool_config, setup_tool_logging, get_logger
# git_branch: refactor/toolkitWorkflow
# git_commit: 21647d6
# === QV-LLM:END ===

"""
QuackTool Configuration and Logging Helpers.

This module provides utilities for QuackTools to load their configuration
and set up logging in a consistent way.
"""

from .base import QuackToolConfigModel
from .loader import load_tool_config, update_tool_config
from .logger import get_logger, setup_tool_logging

__all__ = [
    "QuackToolConfigModel",
    "load_tool_config",
    "update_tool_config",
    "setup_tool_logging",
    "get_logger",
]
