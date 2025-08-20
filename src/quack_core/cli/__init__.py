# quack-core/src/quack-core/cli/__init__.py
"""
CLI package for QuackCore.

This package provides utilities for building command-line interfaces
for QuackVerse tools with consistent behavior and user experience.
"""

# Bootstrap and core functionality
from quackcore.cli.boostrap import from_cli_options, init_cli_env
from quackcore.cli.config import (
    find_project_root,
    load_config,
)
from quackcore.cli.context import QuackContext
from quackcore.cli.error import (
    ensure_single_instance,
    format_cli_error,
    get_cli_info,
    handle_errors,
)

# Text formatting and display
from quackcore.cli.formatting import (
    colorize,
    dict_to_table,
    print_debug,
    print_error,
    print_info,
    print_success,
    print_warning,
    table,
)

# User interaction
from quackcore.cli.interaction import (
    ask,
    ask_choice,
    confirm,
    with_spinner,
)
from quackcore.cli.logging import LoggerFactory, setup_logging
from quackcore.cli.options import CliOptions, resolve_cli_args

# Progress tracking
from quackcore.cli.progress import (
    ProgressCallback,
    ProgressReporter,
    SimpleProgress,
    show_progress,
)

# Terminal utilities
from quackcore.cli.terminal import (
    get_terminal_size,
    supports_color,
    truncate_text,
)

__all__ = [
    # Context and Initialization
    "QuackContext",
    "CliOptions",
    "init_cli_env",
    "from_cli_options",
    # Configuration
    "load_config",
    "find_project_root",
    # Logging
    "setup_logging",
    "LoggerFactory",
    # Error handling
    "format_cli_error",
    "handle_errors",
    "ensure_single_instance",
    "get_cli_info",
    # CLI arguments
    "resolve_cli_args",
    # Formatting and display
    "colorize",
    "print_error",
    "print_warning",
    "print_success",
    "print_info",
    "print_debug",
    "table",
    "dict_to_table",
    # User interaction
    "ask",
    "ask_choice",
    "confirm",
    "with_spinner",
    # Progress tracking
    "show_progress",
    "ProgressReporter",
    "SimpleProgress",
    "ProgressCallback",
    # Terminal utilities
    "get_terminal_size",
    "truncate_text",
    "supports_color",
]
