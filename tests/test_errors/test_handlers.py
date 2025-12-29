# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_errors/test_handlers.py
# role: tests
# neighbors: __init__.py, test_base.py
# exports: TestErrorHandler, TestHandleErrorsDecorator, TestGlobalErrorHandler
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""
Tests for error handling utilities.
"""

import inspect
import sys
from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackError, QuackFileNotFoundError
from quack_core.lib.errors.handlers import ErrorHandler, global_error_handler, handle_errors


class TestErrorHandler:
    """Tests for the ErrorHandler class."""

    def test_format_error_simple(self) -> None:
        """Test formatting a simple exception."""
        handler = ErrorHandler()
        error = Exception("Simple error")

        formatted = handler.format_error(error)
        assert formatted == "Simple error"

    def test_format_quack_error(self) -> None:
        """Test formatting a QuackError with context."""
        handler = ErrorHandler()
        context = {"file": "test.txt", "operation": "read"}
        error = QuackError("Test error", context=context)

        formatted = handler.format_error(error)
        assert "Test error" in formatted
        assert "Context:" in formatted
        assert "file: test.txt" in formatted
        assert "operation: read" in formatted

    def test_format_with_original_error(self) -> None:
        """Test formatting a QuackError with original error."""
        handler = ErrorHandler()
        orig_error = ValueError("Original error")
        error = QuackError("Wrapped error", original_error=orig_error)

        formatted = handler.format_error(error)
        assert "Wrapped error" in formatted
        assert "Original error: " in formatted
        assert "Original error" in formatted

    def test_print_error_with_traceback(self) -> None:
        """Test printing an error with traceback."""
        mock_console = MagicMock()
        handler = ErrorHandler(console=mock_console)
        error = QuackError("Test error")

        # Capture the returned result string
        result = handler.print_error(error, show_traceback=True)

        # Verify console.print was called
        mock_console.print.assert_called_once()
        # Check that the result string contains the error message
        assert "Test error" in result

    def test_handle_error(self) -> None:
        """Test handling an error."""
        mock_console = MagicMock()
        handler = ErrorHandler(console=mock_console)
        error = QuackError("Test error")

        # Capture the returned result string
        result = handler.handle_error(error, title="Custom Title")

        # Verify console.print was called
        mock_console.print.assert_called_once()
        # Check that the result string contains the custom title
        assert "Custom Title" in result

    def test_handle_error_with_exit(self) -> None:
        """Test handling an error with system exit."""
        mock_console = MagicMock()
        handler = ErrorHandler(console=mock_console)
        error = QuackError("Test error")

        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, "exit") as mock_exit:
                mock_exit.side_effect = SystemExit(1)
                handler.handle_error(error, exit_code=1)

        assert excinfo.value.code == 1
        mock_console.print.assert_called_once()

    @staticmethod
    def get_caller_info() -> dict:
        """
        Retrieve information about the caller of the function.

        Returns:
            A dictionary containing the filename, line number, and function name
            of the caller.
        """
        # Use inspect.stack() to get the caller's frame.
        stack = inspect.stack()
        # index 1 corresponds to the caller of get_caller_info
        caller_frame = stack[1]
        return {
            "file": caller_frame.filename,
            "line": caller_frame.lineno,
            "function": caller_frame.function,
        }


class TestHandleErrorsDecorator:
    """Tests for the handle_errors decorator."""

    def test_no_error(self) -> None:
        """Test that the decorator passes through successful execution."""

        @handle_errors()
        def successful_function() -> str:
            return "success"

        assert successful_function() == "success"

    def test_with_specific_error(self) -> None:
        """Test handling a specific error type."""
        mock_console = MagicMock()

        with patch(
            "quack_core.lib.errors.handlers.ErrorHandler",
            return_value=MagicMock(console=mock_console),
        ):

            @handle_errors(error_types=ValueError)
            def function_with_value_error() -> None:
                raise ValueError("Test value error")

            # Should not raise due to the decorator
            result = function_with_value_error()
            assert result is None

    def test_with_multiple_error_types(self) -> None:
        """Test handling multiple error types."""
        mock_console = MagicMock()

        with patch(
            "quack_core.lib.errors.handlers.ErrorHandler",
            return_value=MagicMock(console=mock_console),
        ):

            @handle_errors(error_types=(ValueError, TypeError))
            def function_with_errors() -> None:
                raise TypeError("Test type error")

            # Should not raise due to the decorator
            result = function_with_errors()
            assert result is None

    def test_with_custom_title(self) -> None:
        """Test using a custom title in the decorator."""
        mock_handler = MagicMock()

        with patch("quack_core.lib.errors.handlers.ErrorHandler", return_value=mock_handler):

            @handle_errors(title="Custom Error Title")
            def function_with_error() -> None:
                raise Exception("Test error")

            function_with_error()

            # Verify handler.handle_error was called with the right title
            mock_handler.handle_error.assert_called_once()
            args, kwargs = mock_handler.handle_error.call_args
            assert args[1] == "Custom Error Title"

    def test_with_exit_code(self) -> None:
        """Test using an exit code in the decorator."""
        mock_handler = MagicMock()

        with patch("quack_core.lib.errors.handlers.ErrorHandler", return_value=mock_handler):

            @handle_errors(exit_code=2)
            def function_with_error() -> None:
                raise Exception("Test error")

            function_with_error()

            # Verify handler.handle_error was called with the right exit code
            mock_handler.handle_error.assert_called_once()
            args, kwargs = mock_handler.handle_error.call_args
            assert args[3] == 2


class TestGlobalErrorHandler:
    """Tests for the global error handler."""

    def test_global_handler_exists(self) -> None:
        """Test that the global error handler exists."""
        assert global_error_handler is not None
        assert isinstance(global_error_handler, ErrorHandler)

    def test_global_handler_format_error(self) -> None:
        """Test formatting an error with the global handler."""
        error = QuackFileNotFoundError("/path/to/file")
        formatted = global_error_handler.format_error(error)

        assert "File or directory not found" in formatted
        assert "/path/to/file" in formatted
