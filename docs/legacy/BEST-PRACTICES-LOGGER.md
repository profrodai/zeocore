"""
Example of how to use the quackcore logging module in different scenarios.
"""

# Basic usage with the default logger
from quack_core.core.logging import logger

logger.info("This is a standard log message")
logger.debug("This is a debug message")
logger.warning("This is a warning message")

# Module-specific logger
from quack_core.core.logging import get_logger

module_logger = get_logger(__name__)
module_logger.info("This log comes from a specific module")

# Teaching mode logs (will be specially formatted when Teaching Mode is enabled)
logger.info("[Teaching Mode] This explains how the algorithm works")

# Using log_teaching helper from config
from quack_core.core.logging.config import log_teaching

log_teaching(logger, "Using the log_teaching helper function")

# Configuring a logger with file output
from quack_core.core.logging import configure_logger
from pathlib import Path

file_logger = configure_logger(
    "file_example", 
    log_file=Path("logs/quack_core.log")
)
file_logger.info("This message goes to both console and file")

# Setting custom log level
import logging
custom_logger = configure_logger("verbose_module", level=logging.DEBUG)
custom_logger.debug("This debug message will be shown regardless of environment settings")

# Using different verbosity levels in Teaching Mode
logger.debug("[Teaching Mode] Detailed explanation of internal workings")