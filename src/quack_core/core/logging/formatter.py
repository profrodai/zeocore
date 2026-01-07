# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/logging/formatter.py
# module: quack_core.core.logging.formatter
# role: module
# neighbors: __init__.py, config.py, logger.py
# exports: Colors, VerbosityLevel, TeachingProvider, DefaultTeachingProvider, TeachingAwareFormatter, set_teaching_provider, reset_teaching_provider
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===




"""
Custom formatters for quack-core logging.

This module provides formatters that adapt log output based on Teaching Mode
status and verbosity levels via an injected provider.
"""

import logging
from enum import Enum
from typing import Protocol

# Constant key used in the 'extra' dict of log records to identify teaching logs
TEACHING_EXTRA_KEY = "quack_teaching"


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"


class VerbosityLevel(str, Enum):
    BASIC = "BASIC"
    VERBOSE = "VERBOSE"
    DEBUG = "DEBUG"


class TeachingProvider(Protocol):
    """Protocol for checking Teaching Mode state."""

    def is_enabled(self) -> bool: ...

    def get_level(self) -> VerbosityLevel: ...


class DefaultTeachingProvider:
    """Default provider that always returns disabled state."""

    def is_enabled(self) -> bool:
        return False

    def get_level(self) -> VerbosityLevel:
        return VerbosityLevel.BASIC


# Global mutable provider to allow injection after import
_teaching_provider: TeachingProvider = DefaultTeachingProvider()


def set_teaching_provider(provider: TeachingProvider) -> None:
    """Inject a teaching provider."""
    global _teaching_provider
    _teaching_provider = provider


def reset_teaching_provider() -> None:
    """Reset the global teaching provider to default. Useful for test cleanup."""
    global _teaching_provider
    _teaching_provider = DefaultTeachingProvider()


class TeachingAwareFormatter(logging.Formatter):
    """
    Custom formatter that enhances log messages based on Teaching Mode status.
    """

    DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(
            self,
            fmt: str | None = None,
            datefmt: str | None = None,
            color_enabled: bool = True,
            teaching_provider: TeachingProvider | None = None,
    ):
        """
        Initialize the formatter.

        Args:
            fmt: Log format string.
            datefmt: Date format string.
            color_enabled: Whether to use ANSI colors.
            teaching_provider: Optional specific provider instance. If None,
                               uses the global singleton.
        """
        super().__init__(fmt or self.DEFAULT_FORMAT, datefmt or self.DATE_FORMAT)
        self.color_enabled = color_enabled
        self.teaching_provider = teaching_provider

    def format(self, record: logging.LogRecord) -> str:
        formatted_msg = super().format(record)
        formatted_msg = self._apply_level_formatting(record, formatted_msg)

        # Detect Teaching Mode via the structured 'extra' attribute
        # falling back to string check only for backwards compatibility/safety
        is_teaching = (
                getattr(record, TEACHING_EXTRA_KEY, False)
                or "[Teaching Mode]" in record.getMessage()
        )

        if is_teaching:
            return self._format_teaching_log(formatted_msg)

        return formatted_msg

    def _apply_level_formatting(self, record: logging.LogRecord, msg: str) -> str:
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
            level_str = f"[{record.levelname}]"
            colored_level = f"{color}[{record.levelname}]{Colors.RESET}"
            return msg.replace(level_str, colored_level)

        return msg

    def _format_teaching_log(self, msg: str) -> str:
        # Use instance provider if set, otherwise fallback to global
        provider = self.teaching_provider or _teaching_provider

        if not provider.is_enabled():
            return msg

        verbosity = provider.get_level()

        if not self.color_enabled:
            return f"🦆 {msg}"

        verbosity_formatting = {
            VerbosityLevel.BASIC: f"{Colors.CYAN}🦆 {msg}{Colors.RESET}",
            VerbosityLevel.VERBOSE: f"{Colors.MAGENTA}🦆 {Colors.BOLD}[VERBOSE]{Colors.RESET} {msg}",
            VerbosityLevel.DEBUG: f"{Colors.BLUE}🦆 {Colors.BOLD}[DEBUG]{Colors.RESET} {msg}",
        }

        return verbosity_formatting.get(verbosity, f"🦆 {msg}")