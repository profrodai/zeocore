# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_error.py
# role: tests
# neighbors: __init__.py, mocks.py, test_bootstrap.py, test_config.py, test_context.py, test_formatting.py (+5 more)
# exports: TestFormatCliError, TestHandleErrors, TestEnsureSingleInstance, TestGetCliInfo
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Tests for the CLI error handling module.
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from quack_core.interfaces.cli.utils.error import (
    ensure_single_instance,
    format_cli_error,
    get_cli_info,
    handle_errors,
)
from quack_core.lib.errors import QuackError


class TestFormatCliError:
    """Tests for format_cli_error function."""

    def test_format_basic_error(self) -> None:
        """Test formatting a basic exception."""
        error = Exception("Basic error message")
        result = format_cli_error(error)
        assert result == "Basic error message"

    def test_format_quack_error(self) -> None:
        """Test formatting a QuackError."""
        # Create a QuackError with context
        context = {"file": "test.py", "line": 42}
        error = QuackError("Quack error message", context=context)

        result = format_cli_error(error)

        assert "Quack error message" in result
        assert "Context:" in result
        assert "file: test.py" in result
        assert "line: 42" in result

    def test_format_error_with_original(self) -> None:
        """Test formatting a QuackError with original error."""
        original = ValueError("Original error")
        error = QuackError("Wrapped error", original_error=original)

        result = format_cli_error(error)

        assert "Wrapped error" in result
        assert "Original error: Original error" in result


class TestHandleErrors:
    """Tests for handle_errors decorator."""

    def test_basic_decorator(self) -> None:
        """Test basic usage of the decorator."""
        # Mock the print_error function BEFORE defining functions with decorators
        with patch("quack_core.interfaces.cli.utils.error._print_error") as mock_print_error:
            # Define a function with the decorator
            @handle_errors()
            def successful_function() -> str:
                return "success"

            # Test successful execution
            result = successful_function()
            assert result == "success"

            # Define a function that raises an error
            @handle_errors()
            def failing_function() -> None:
                raise ValueError("Test error")

            # Call the function
            result = failing_function()

            # Verify the function returns None and prints the error
            assert result is None
            mock_print_error.assert_called_once()
            # The error message should include the function name
            assert "Error in failing_function" in mock_print_error.call_args[0][0]

    def test_with_specific_error_types(self) -> None:
        """Test specifying error types to catch."""
        with patch("quack_core.interfaces.cli.utils.error._print_error") as mock_print_error:
            # Define a function that catches only ValueError
            @handle_errors(error_types=ValueError)
            def value_error_function() -> None:
                raise ValueError("Value error")

            # Define a function that catches multiple error types
            @handle_errors(error_types=(ValueError, TypeError))
            def multiple_error_function() -> None:
                raise TypeError("Type error")

            # Call the functions
            value_error_function()
            multiple_error_function()

            # Verify print_error was called twice
            assert mock_print_error.call_count == 2

        # Define a function that raises an uncaught error
        @handle_errors(error_types=ValueError)
        def uncaught_error_function() -> None:
            raise TypeError("Type error")

        # This should raise the TypeError
        with pytest.raises(TypeError):
            uncaught_error_function()

    def test_with_custom_title(self) -> None:
        """Test using a custom error title."""
        with patch("quack_core.interfaces.cli.utils.error._print_error") as mock_print_error:

            @handle_errors(title="Custom Error Title")
            def custom_title_function() -> None:
                raise ValueError("Test error")

            custom_title_function()

            # Verify the custom title was used
            assert "Custom Error Title" in mock_print_error.call_args[0][0]

    def test_with_traceback(self) -> None:
        """Test showing traceback."""
        with patch("quack_core.interfaces.cli.utils.error._print_error") as mock_print_error:
            with patch("traceback.print_exc") as mock_print_exc:

                @handle_errors(show_traceback=True)
                def traceback_function() -> None:
                    raise ValueError("Test error")

                traceback_function()

                # Verify traceback was printed
                mock_print_exc.assert_called_once()

    def test_with_exit_code(self) -> None:
        """Test exiting with specific code."""
        with patch("quack_core.interfaces.cli.utils.error._print_error") as mock_print_error:
            with patch("sys.exit") as mock_exit:

                @handle_errors(exit_code=42)
                def exit_function() -> None:
                    raise ValueError("Test error")

                exit_function()

                # Verify sys.exit was called with the right code
                mock_exit.assert_called_once_with(42)


class TestEnsureSingleInstance:
    """Tests for ensure_single_instance function."""

    def test_first_instance(self) -> None:
        """Test when this is the first instance."""
        with patch("socket.socket") as mock_socket:
            # Mock socket binding to succeed
            mock_socket_instance = MagicMock()
            mock_socket.return_value = mock_socket_instance

            with patch("os.path.join", return_value="/tmp/test_app.lock") as mock_join:
                # Fix: Patch builtins.open instead of just "open"
                with patch("builtins.open", create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_open.return_value.__enter__.return_value = mock_file

                    with patch("atexit.register") as mock_register:
                        result = ensure_single_instance("test_app")

                        # Verify result and function calls
                        assert result is True
                        mock_socket_instance.bind.assert_called_once()
                        mock_join.assert_called_once()
                        mock_open.assert_called_once()
                        mock_file.write.assert_called_once()
                        mock_register.assert_called_once()

    def test_already_running(self) -> None:
        """Test when an instance is already running."""
        with patch("socket.socket") as mock_socket:
            # Mock socket binding to fail
            mock_socket_instance = MagicMock()
            mock_socket_instance.bind.side_effect = OSError("Address already in use")
            mock_socket.return_value = mock_socket_instance

            result = ensure_single_instance("test_app")

            # Verify result
            assert result is False
            mock_socket_instance.bind.assert_called_once()

    def test_cleanup_on_exit(self) -> None:
        """Test that cleanup function is registered and works."""
        with patch("socket.socket") as mock_socket:
            # Mock socket binding to succeed
            mock_socket_instance = MagicMock()
            mock_socket.return_value = mock_socket_instance

            with patch("os.path.join", return_value="/tmp/test_app.lock") as mock_join:
                # Fix: Patch builtins.open instead of just "open"
                with patch("builtins.open", create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_open.return_value.__enter__.return_value = mock_file

                    with patch("os.remove") as mock_remove:
                        with patch("atexit.register") as mock_register:
                            # Create a container to hold the cleanup function
                            class FuncCapture:
                                cleanup_func = None

                            # Capture the cleanup function
                            def capture_cleanup(func):
                                FuncCapture.cleanup_func = func
                                return None  # Return value for the register mock

                            mock_register.side_effect = capture_cleanup

                            ensure_single_instance("test_app")

                            # Call the captured cleanup function
                            FuncCapture.cleanup_func()

                            # Verify socket was closed and lock file was deleted
                            mock_socket_instance.close.assert_called_once()
                            mock_remove.assert_called_once_with("/tmp/test_app.lock")

    def test_port_calculation(self) -> None:
        """Test that port is calculated from app name."""
        # Test with different app names to verify different ports
        with patch("socket.socket") as mock_socket:
            # Create a socket instance that records the port
            mock_socket_instance = MagicMock()
            port_values = []

            def record_port(addr):
                host, port = addr
                port_values.append(port)

            mock_socket_instance.bind.side_effect = record_port
            mock_socket.return_value = mock_socket_instance

            with patch("os.path.join", return_value="/tmp/test_app.lock"):
                # Fix: Patch builtins.open instead of just "open"
                with patch("builtins.open", create=True):
                    with patch("atexit.register"):
                        # Call with different app names
                        ensure_single_instance("app1")
                        ensure_single_instance("app2")

                        # Verify different ports were used
                        assert port_values[0] != port_values[1]
                        # Verify ports are in the expected range (10000-20000)
                        assert 10000 <= port_values[0] < 20000
                        assert 10000 <= port_values[1] < 20000


class TestGetCliInfo:
    """Tests for get_cli_info function."""

    def test_basic_info(self) -> None:
        """Test getting basic CLI information."""
        # Since we can't directly patch datetime.datetime.now in Python 3.13,
        # we'll patch our helper function instead
        fixed_datetime = datetime(2023, 1, 1, 12, 0, 0)

        # Mock various functions
        with patch("platform.platform", return_value="Test Platform"):
            with patch("platform.python_version", return_value="3.13.0"):
                # Patch our helper function instead of datetime.datetime.now
                with patch(
                    "quack_core.interfaces.cli.utils.error._get_current_datetime",
                    return_value=fixed_datetime,
                ):
                    with patch("os.getpid", return_value=12345):
                        with patch("os.getcwd", return_value="/current/dir"):
                            with patch(
                                "quack_core.config.utils.get_env", return_value="test"
                            ):
                                with patch(
                                    "quack_core.interfaces.cli.utils.terminal.get_terminal_size"
                                ) as mock_term_size:
                                    mock_term_size.return_value = (80, 24)

                                    with patch.dict(os.environ, {"USER": "testuser"}):
                                        # Call the function under test
                                        info = get_cli_info()

                                        # Verify the returned information
                                        assert info["platform"] == "Test Platform"
                                        assert info["python_version"] == "3.13.0"
                                        assert info["time"] == "2023-01-01T12:00:00"
                                        assert info["pid"] == 12345
                                        assert info["cwd"] == "/current/dir"
                                        assert info["environment"] == "test"
                                        assert info["terminal_size"] == "80x24"
                                        assert info["username"] == "testuser"
                                        assert info["is_ci"] is False

    def test_terminal_size_error(self) -> None:
        """Test handling errors getting terminal size."""
        with patch("platform.platform"):
            with patch("platform.python_version"):
                with patch(
                    "quack_core.interfaces.cli.utils.error._get_current_datetime",
                    return_value=datetime(2023, 1, 1, 12, 0, 0),
                ):
                    with patch("os.getpid"):
                        with patch("os.getcwd"):
                            with patch("quack_core.config.utils.get_env"):
                                with patch(
                                    "quack_core.interfaces.cli.utils.terminal.get_terminal_size"
                                ) as mock_term_size:
                                    # Simulate an error getting terminal size
                                    mock_term_size.side_effect = OSError(
                                        "Terminal error"
                                    )

                                    # Call the function under test
                                    info = get_cli_info()

                                    # Verify terminal_size is "unknown"
                                    assert info["terminal_size"] == "unknown"

    def test_ci_detection(self) -> None:
        """Test detecting CI environments."""
        with patch("platform.platform"):
            with patch("platform.python_version"):
                with patch(
                    "quack_core.interfaces.cli.utils.error._get_current_datetime",
                    return_value=datetime(2023, 1, 1, 12, 0, 0),
                ):
                    with patch("os.getpid"):
                        with patch("os.getcwd"):
                            with patch("quack_core.config.utils.get_env"):
                                # Make sure get_terminal_size returns a valid tuple
                                with patch(
                                    "quack_core.interfaces.cli.utils.terminal.get_terminal_size",
                                    return_value=(80, 24),
                                ):
                                    # Test various CI environment variables
                                    for env_var in [
                                        "CI",
                                        "GITHUB_ACTIONS",
                                        "GITLAB_CI",
                                    ]:
                                        with patch.dict(os.environ, {env_var: "true"}):
                                            info = get_cli_info()
                                            assert info["is_ci"] is True
