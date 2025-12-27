# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/interfaces/cli/utils/options.py
# module: quack_core.interfaces.cli.utils.options
# role: utils
# neighbors: __init__.py, error.py, formatting.py, interaction.py, logging.py, progress.py (+1 more)
# exports: CliOptions, resolve_cli_args
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
CLI options and argument processing utilities.

This module provides data models and utilities for handling command-line
arguments and options in a consistent way across QuackCore CLI tools.
"""

from collections.abc import Sequence
from typing import Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")  # Generic type for flexible typing

# Define LogLevel type for better type checking
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class CliOptions(BaseModel):
    """
    CLI options that can affect bootstrapping behavior.

    This model represents command-line options that can override configuration
    and control runtime behavior like logging and debugging.
    """

    config_path: str | None = Field(
        default=None, description="Path to configuration file"
    )
    log_level: LogLevel | None = Field(default=None, description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(default=False, description="Enable verbose output")
    quiet: bool = Field(default=False, description="Suppress non-error output")
    environment: str | None = Field(
        default=None, description="Override the environment"
    )
    base_dir: str | None = Field(
        default=None, description="Override the base directory"
    )
    no_color: bool = Field(default=False, description="Disable colored output")

    model_config = {
        "frozen": True,
        "extra": "ignore",
    }


def resolve_cli_args(args: Sequence[str]) -> dict[str, object]:
    """
    Parse common CLI arguments into a dictionary.

    CLI overrides are parsed, and positional arguments are collected under the
    empty string key "".

    Args:
        args: Sequence of command-line arguments

    Returns:
        Dictionary of parsed arguments
    """
    result: dict[str, object] = {}
    pos: list[str] = []
    i = 0
    separator = False
    # Long option names treated as boolean flags
    flag_names = {"debug", "verbose", "quiet", "no-color", "help", "version"}

    while i < len(args):
        arg = args[i]
        # After '--', everything is positional
        if separator:
            pos.append(arg)
            i += 1
            continue
        # Handle '--' separator
        if arg == "--":
            separator = True
            i += 1
            continue
        # Long options: --name or --name=value
        if arg.startswith("--"):
            name_val = arg[2:]
            # --name=value
            if "=" in name_val:
                name, value = name_val.split("=", 1)
                result[name] = value
                i += 1
                continue
            name = name_val
            # Boolean flag
            if name in flag_names:
                result[name] = True
                i += 1
                continue
            # Option with separate value - check if next arg exists and is not separator
            # Accept the value even if it starts with '--' (could be a value like '--0')
            if i + 1 < len(args) and args[i + 1] != "--":
                result[name] = args[i + 1]
                i += 2
                continue
            # Fallback to boolean
            result[name] = True
            i += 1
            continue
        # Short options: -abc or -a
        if (
            arg.startswith("-")
            and len(arg) > 1
            and not arg.startswith("--")
            and all(c.isalpha() for c in arg[1:])
        ):
            chars = list(arg[1:])
            # Process all but last as flags
            for c in chars[:-1]:
                result[c] = True
            last = chars[-1]
            # Last char consumes the next token as its value, if present
            if i + 1 < len(args):
                result[last] = args[i + 1]
                i += 2
            else:
                result[last] = True
                i += 1
            continue
        # Positional argument
        pos.append(arg)
        i += 1
    if pos:
        result[""] = pos
    return result
