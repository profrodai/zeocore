# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/errors/handlers.py
# module: quack_core.core.errors.handlers
# role: module
# neighbors: __init__.py, base.py, integration.py
# exports: ErrorHandler, handle_errors
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

"""
Error handling utilities for quack_core.

This module provides utilities for handling and formatting errors in a consistent way,
making it easier to diagnose and fix issues in the Quack ecosystem.
"""

import inspect
import sys
import traceback
from collections.abc import Callable
from typing import TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.traceback import Traceback

from quack_core.core.errors.base import QuackError

T = TypeVar("T")


class ErrorHandler:
    """
    Handles and formats errors for better diagnostics.

    This class provides utilities for handling errors in a consistent way,
    with detailed diagnostics and formatted output.
    """

    def __init__(self, console: Console | None = None) -> None:
        """
        Initialize the error handler.

        Args:
            console: A Rich console instance, or None to create a new one
        """
        self.console = console or Console(stderr=True)

    def format_error(self, error: Exception) -> str:
        """
        Format an error for display.
        """
        if isinstance(error, QuackError):
            return self._format_quack_error(error)
        return str(error)

    def _format_quack_error(self, error: QuackError) -> str:
        """
        Format a QuackError with context information.
        """
        message = str(error)
        result = [message]

        if error.context:
            result.append("\nContext:")
            for key, value in error.context.items():
                result.append(f"  {key}: {value}")

        if error.original_error and error.original_error is not error:
            result.append(f"\nOriginal error: {error.original_error}")

        return "\n".join(result)

    def print_error(
            self, error: Exception, title: str | None = None,
            show_traceback: bool = False
    ) -> str:
        """
        Print an error to the console using Rich panels.
        """
        error_title = title or f"[bold red]{type(error).__name__}[/bold red]"
        formatted_error = self.format_error(error)
        panel_content = formatted_error

        if show_traceback and error.__traceback__:
            # Attempt to use Rich's beautiful traceback
            tb = Traceback.from_exception(type(error), error, error.__traceback__)
            # Note: We can't easily concatenate string + Traceback object in one panel content string.
            # We print them separately or use a RenderGroup/Group.
            # For simplicity in this kernel utility, we rely on printing directly.

            # Print the error message panel first
            self.console.print(
                Panel(panel_content, title=error_title, border_style="red")
            )
            # Then print the traceback
            self.console.print(tb)

            # Update panel_content for the return value (legacy test support)
            trace_str = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            return f"{error_title}\n{formatted_error}\n\nTraceback:\n{trace_str}"
        else:
            self.console.print(
                Panel(formatted_error, title=error_title, border_style="red")
            )
            return f"{error_title}\n{formatted_error}"

    def handle_error(
            self,
            error: Exception,
            title: str | None = None,
            show_traceback: bool = False,
            exit_code: int | None = None,
    ) -> str:
        """
        Handle an error by printing it and optionally exiting.
        """
        output = self.print_error(error, title, show_traceback)
        if exit_code is not None:
            sys.exit(exit_code)
        return output


def handle_errors(
        error_types: type[Exception] | tuple[type[Exception], ...] = Exception,
        title: str | None = None,
        show_traceback: bool = False,
        exit_code: int | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """
    Decorator to handle errors in a function.
    Instantiates a transient ErrorHandler to avoid global state.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        def wrapper(*args: object, **kwargs: object) -> T | None:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                handler = ErrorHandler()
                func_title = title or f"Error in {func.__name__}"
                handler.handle_error(e, func_title, show_traceback, exit_code)
                return None

        return wrapper

    return decorator