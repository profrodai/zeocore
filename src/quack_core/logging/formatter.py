# quack-core/src/quack_core/logging/formatter.py
"""
Custom formatters for quack-core logging.

This module provides formatters that adapt log output based on Teaching Mode
status and verbosity levels.
"""

import logging
from enum import Enum


# Define ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"


# Enum for verbosity levels that may be used in Teaching Mode
class VerbosityLevel(str, Enum):
    BASIC = "BASIC"
    VERBOSE = "VERBOSE"
    DEBUG = "DEBUG"


# Since quackster doesn't exist yet, we stub the required functions
def teaching_is_enabled() -> bool:
    """
    Stub function to check if Teaching Mode is enabled.

    This will be replaced with an actual implementation when quackster
    module is created.

    Returns:
        Always False until quackster module is implemented
    """
    # TODO: Replace with actual implementation once quackster exists
    return False


def teaching_get_level() -> VerbosityLevel:
    """
    Stub function to get the current Teaching Mode verbosity level.

    This will be replaced with an actual implementation when quackster
    module is created.

    Returns:
        Always VerbosityLevel.BASIC until quackster module is implemented
    """
    # TODO: Replace with actual implementation once quackster exists
    return VerbosityLevel.BASIC


class TeachingAwareFormatter(logging.Formatter):
    """
    Custom formatter that enhances log messages based on Teaching Mode status.

    This formatter applies special formatting to Teaching Mode logs and handles
    different verbosity levels.
    """

    DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        color_enabled: bool = True,
    ):
        """
        Initialize the formatter with optional custom formats.

        Args:
            fmt: Custom format string (optional)
            datefmt: Custom date format string (optional)
            color_enabled: Whether to use ANSI color codes (default: True)
        """
        super().__init__(fmt or self.DEFAULT_FORMAT, datefmt or self.DATE_FORMAT)
        self.color_enabled = color_enabled

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record, with special handling for Teaching Mode logs.

        Args:
            record: The log record to format

        Returns:
            The formatted log message
        """
        # Get the basic formatted message
        formatted_msg = super().format(record)

        # Apply level-based formatting
        formatted_msg = self._apply_level_formatting(record, formatted_msg)

        # Apply Teaching Mode formatting if applicable
        if "[Teaching Mode]" in record.getMessage():
            return self._format_teaching_log(formatted_msg)

        return formatted_msg

    def _apply_level_formatting(self, record: logging.LogRecord, msg: str) -> str:
        """
        Apply formatting based on the log level.

        Args:
            record: The log record
            msg: The formatted message

        Returns:
            The formatted message with level-specific styling
        """
        if not self.color_enabled:
            return msg

        level_colors = {
            logging.DEBUG: Colors.BLUE,
            logging.INFO: Colors.GREEN,
            logging.WARNING: Colors.YELLOW,
            logging.ERROR: Colors.RED,
            logging.CRITICAL: Colors.BOLD + Colors.RED,
        }

        color = level_colors.get(record.levelno, "")
        if color:
            # Apply color to the level name portion of the message
            level_str = f"[{record.levelname}]"
            colored_level = f"{color}[{record.levelname}]{Colors.RESET}"
            return msg.replace(level_str, colored_level)

        return msg

    def _format_teaching_log(self, msg: str) -> str:
        """
        Apply special formatting to Teaching Mode logs.

        Args:
            msg: The formatted message

        Returns:
            The message with Teaching Mode specific formatting
        """
        # Check if Teaching Mode is enabled (using stub for now)
        if not teaching_is_enabled():
            return msg

        # Get Teaching Mode verbosity level (using stub for now)
        verbosity = teaching_get_level()

        # Basic Teaching Mode formatting
        if not self.color_enabled:
            return f"🦆 {msg}"

        # Apply color based on verbosity
        verbosity_formatting = {
            VerbosityLevel.BASIC: f"{Colors.CYAN}🦆 {msg}{Colors.RESET}",
            VerbosityLevel.VERBOSE: f"{Colors.MAGENTA}🦆 {Colors.BOLD}[VERBOSE]{Colors.RESET} {msg}",
            VerbosityLevel.DEBUG: f"{Colors.BLUE}🦆 {Colors.BOLD}[DEBUG]{Colors.RESET} {msg}",
        }

        return verbosity_formatting.get(verbosity, f"🦆 {msg}")
