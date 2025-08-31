# quack-core/src/quack-core/cli/__init__.py
"""
CLI package for quack_core.

This package provides utilities for building command-line interfaces
for QuackVerse tools with consistent behavior and user experience.
"""

# Bootstrap and core functionality
from quack_core.cli.boostrap import from_cli_options, init_cli_env
from quack_core.cli.config import (
    find_project_root,
    load_config,
)
from quack_core.cli.context import QuackContext
from quack_core.cli.error import (
    ensure_single_instance,
    format_cli_error,
    get_cli_info,
    handle_errors,
)

# Text formatting and display
from quack_core.cli.formatting import (
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
from quack_core.cli.interaction import (
    ask,
    ask_choice,
    confirm,
    with_spinner,
)
from quack_core.cli.logging import LoggerFactory, setup_logging
from quack_core.cli.options import CliOptions, resolve_cli_args

# Progress tracking
from quack_core.cli.progress import (
    ProgressCallback,
    ProgressReporter,
    SimpleProgress,
    show_progress,
)

# Terminal utilities
from quack_core.cli.terminal import (
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
