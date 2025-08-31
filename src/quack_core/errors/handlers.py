# quack-core/src/quack-core/errors/handlers.py
"""
Error handling utilities for quack_core.

This module provides utilities for handling and formatting errors in a consistent way,
making it easier to diagnose and fix issues in the Quack ecosystem.
"""

import inspect
import sys
from collections.abc import Callable
from typing import TypeVar

from rich.console import Console
from rich.panel import Panel

from quack_core.errors.base import QuackError

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

        Args:
            error: The exception to format

        Returns:
            A formatted error message
        """
        if isinstance(error, QuackError):
            return self._format_quack_error(error)
        return str(error)

    def _format_quack_error(self, error: QuackError) -> str:
        """
        Format a QuackError for display.

        Args:
            error: The QuackError to format

        Returns:
            A formatted error message with context information
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

    # In src/quack-core/errors/handlers.py

    # In src/quack-core/errors/handlers.py
    def print_error(
        self, error: Exception, title: str | None = None, show_traceback: bool = False
    ) -> str:
        """
        Print an error to the console.

        Args:
            error: The exception to print
            title: An optional title for the error panel
            show_traceback: Whether to show the traceback

        Returns:
            The formatted error message (for testing)
        """
        import traceback  # Import outside the try block so it's always available

        error_title = title or f"[bold red]{type(error).__name__}[/bold red]"
        formatted_error = self.format_error(error)
        panel_content = formatted_error

        if show_traceback and error.__traceback__:
            try:
                from rich.traceback import Traceback

                # Create a properly formatted traceback that can be displayed in Rich
                tb = Traceback.from_exception(type(error), error, error.__traceback__)
                panel_content = f"{formatted_error}\n\n{tb}"
                # For test compatibility, render as string first
                rendered_panel = Panel(
                    panel_content,
                    title=error_title,
                    border_style="red",
                )
                self.console.print(rendered_panel)
            except ImportError:
                # Only catch ImportError for more specific exception handling
                # This is for when rich.traceback might not be available
                trace_str = "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                )
                panel_content = f"{formatted_error}\n\nTraceback:\n{trace_str}"
                # For test compatibility, render as string first
                rendered_panel = Panel(
                    panel_content,
                    title=error_title,
                    border_style="red",
                )
                self.console.print(rendered_panel)
        else:
            # For test compatibility, render as string first
            rendered_panel = Panel(
                formatted_error,
                title=error_title,
                border_style="red",
            )
            self.console.print(rendered_panel)

        # Return content for testing, including title for test validation
        return f"{error_title}\n{panel_content}"

    def get_caller_info(self, depth: int = 1) -> dict[str, object]:
        """
        Get information about the caller of a function.

        Args:
            depth: How many frames to go back in the call stack

        Returns:
            A dictionary with caller information
        """
        frame = inspect.currentframe()
        if frame is None:
            return {}

        # Go back 'depth' frames
        try:
            for _ in range(depth + 1):
                if frame.f_back is None:
                    break
                frame = frame.f_back

            # Get caller information
            frame_info = inspect.getframeinfo(frame)

            # Get the name of the function that called us
            # We need to look at the code context to get
            # the actual function name in nested functions
            context = (
                frame_info.code_context[0].strip() if frame_info.code_context else ""
            )
            calling_function = frame_info.function

            # If this is a nested function,
            # the calling function name will be the outer function
            # We need to extract the inner function name from the context
            if "def " in context:
                # Extract function name from 'def function_name'
                function_name = context.split("def ")[1].split("(")[0].strip()
                # Use the inner function name if we found one
                if function_name:
                    calling_function = function_name

            return {
                "file": frame_info.filename,
                "line": frame_info.lineno,
                "function": calling_function,
                "code": context,
                "module": inspect.getmodule(frame).__name__
                if inspect.getmodule(frame)
                else None,
            }
        finally:
            # Clean up references to avoid memory leaks
            del frame

    # In src/quack-core/errors/handlers.py
    def handle_error(
        self,
        error: Exception,
        title: str | None = None,
        show_traceback: bool = False,
        exit_code: int | None = None,
    ) -> str:
        """
        Handle an error by printing it and optionally exiting.

        Args:
            error: The exception to handle
            title: An optional title for the error panel
            show_traceback: Whether to show the traceback
            exit_code: If provided, exit with this code after handling the error

        Returns:
            The formatted error message (for testing)
        """
        panel_content = self.print_error(error, title, show_traceback)
        if exit_code is not None:
            sys.exit(exit_code)
        return panel_content


def handle_errors(
    error_types: type[Exception] | tuple[type[Exception], ...] = Exception,
    title: str | None = None,
    show_traceback: bool = False,
    exit_code: int | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """
    Decorator to handle errors in a function.

    Args:
        error_types: The exception type(s) to catch
        title: An optional title for the error panel
        show_traceback: Whether to show the traceback
        exit_code: If provided, exit with this code after handling the error

    Returns:
        A decorator function
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


# Create a global instance for convenience
global_error_handler = ErrorHandler()
