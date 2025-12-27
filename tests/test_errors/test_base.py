# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_errors/test_base.py
# role: tests
# neighbors: __init__.py, test_handlers.py
# exports: TestQuackError, TestQuackIOError, TestSpecificErrors, TestWrapIOErrors
# git_branch: refactor/newHeaders
# git_commit: bd13631
# === QV-LLM:END ===

"""
Tests for QuackCore error classes and decorators.
"""

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from quack_core.lib.errors import (
    QuackBaseAuthError,
    QuackConfigurationError,
    QuackError,
    QuackFileExistsError,
    QuackFileNotFoundError,
    QuackFormatError,
    QuackIOError,
    QuackPermissionError,
    QuackPluginError,
    QuackValidationError,
    wrap_io_errors,
)


class TestQuackError:
    """Tests for the base QuackError class."""

    def test_basic_functionality(self) -> None:
        """Test creating a QuackError with just a message."""
        error = QuackError("Test error message")

        assert str(error) == "Test error message"
        assert error.context == {}
        assert error.original_error is None

    @given(st.text(min_size=1), st.dictionaries(st.text(), st.text()))
    def test_with_context(self, message: str, context: dict[str, str]) -> None:
        """Test QuackError with a message and context dictionary."""
        error = QuackError(message, context=context)

        assert error.context == context
        # Check that context info is included in the string representation
        if context:
            assert all(key in str(error) for key in context.keys())

    def test_with_original_error(self) -> None:
        """Test QuackError with an original exception."""
        original = ValueError("Original error")
        error = QuackError("Wrapped error", original_error=original)

        assert error.original_error is original
        assert "Wrapped error" in str(error)

    def test_exception_chaining(self) -> None:
        """Test that exception chaining works correctly."""
        original = ValueError("Original error")

        try:
            try:
                raise original
            except ValueError as e:
                raise QuackError("Wrapped error", original_error=e) from e
        except QuackError as e:
            assert e.__cause__ is original
            assert e.original_error is original


class TestQuackIOError:
    """Tests for QuackIOError."""

    def test_with_string_path(self) -> None:
        """Test creating a QuackIOError with a string path."""
        error = QuackIOError("IO error message", "/path/to/file")

        assert error.path == "/path/to/file"
        assert "path='/path/to/file'" in str(error)

    def test_with_path_object(self) -> None:
        """Test creating a QuackIOError with a Path object."""
        path = Path("/path/to/file")
        error = QuackIOError("IO error message", path)

        assert error.path == str(path)
        assert "path='/path/to/file'" in str(error)


class TestSpecificErrors:
    """Tests for specific error subclasses."""

    def test_file_not_found_error(self) -> None:
        """Test QuackFileNotFoundError."""
        error = QuackFileNotFoundError("/path/to/missing/file")

        assert "File or directory not found" in str(error)
        assert error.path == "/path/to/missing/file"

        # Test with custom message
        custom_error = QuackFileNotFoundError("/path/to/file", "Custom message")
        assert "Custom message" in str(custom_error)

    def test_permission_error(self) -> None:
        """Test QuackPermissionError."""
        error = QuackPermissionError("/path/to/file", "read")

        assert "Permission denied for read operation" in str(error)
        assert error.path == "/path/to/file"
        assert error.operation == "read"

    def test_file_exists_error(self) -> None:
        """Test QuackFileExistsError."""
        error = QuackFileExistsError("/path/to/existing/file")

        assert "File or directory already exists" in str(error)
        assert error.path == "/path/to/existing/file"

    def test_validation_error(self) -> None:
        """Test QuackValidationError."""
        errors = {"field1": ["Value too short"], "field2": ["Invalid format"]}
        error = QuackValidationError("Validation failed", "/path/to/file", errors)

        assert "Validation failed" in str(error)
        assert error.path == "/path/to/file"
        assert error.errors == errors

    def test_format_error(self) -> None:
        """Test QuackFormatError."""
        error = QuackFormatError("/path/to/file", "JSON")

        assert "Invalid JSON format" in str(error)
        assert error.path == "/path/to/file"
        assert error.format_name == "JSON"

    def test_configuration_error(self) -> None:
        """Test QuackConfigurationError."""
        error = QuackConfigurationError(
            "Config error", "/path/to/config.yaml", "database.url"
        )

        assert "Config error" in str(error)
        assert error.config_path == "/path/to/config.yaml"
        assert error.config_key == "database.url"

    def test_plugin_error(self) -> None:
        """Test QuackPluginError."""
        error = QuackPluginError("Plugin error", "test_plugin", "/path/to/plugin.py")

        assert "Plugin error" in str(error)
        assert error.plugin_name == "test_plugin"
        assert error.plugin_path == "/path/to/plugin.py"

    def test_authentication_error(self) -> None:
        """Test QuackAuthenticationError."""
        error = QuackBaseAuthError(
            "Auth error", "Google Drive", "/path/to/credentials.json"
        )

        assert "Auth error" in str(error)
        assert error.service == "Google Drive"
        assert error.credentials_path == "/path/to/credentials.json"


class TestWrapIOErrors:
    """Tests for wrap_io_errors decorator."""

    def test_basic_wrapping(self) -> None:
        """Test that normal execution passes through the decorator."""

        @wrap_io_errors
        def normal_function() -> str:
            return "success"

        assert normal_function() == "success"

    def test_value_error_wrapping(self) -> None:
        """Test that ValueError is converted to QuackValidationError."""

        @wrap_io_errors
        def function_with_value_error() -> None:
            raise ValueError("Invalid value")

        with pytest.raises(QuackValidationError) as excinfo:
            function_with_value_error()

        assert "Invalid value" in str(excinfo.value)
        assert isinstance(excinfo.value.original_error, ValueError)

    def test_file_not_found_wrapping(self) -> None:
        """Test that FileNotFoundError is converted to QuackFileNotFoundError."""
        file_path = "/path/to/nonexistent/file"

        @wrap_io_errors
        def function_with_file_not_found() -> None:
            # Create a FileNotFoundError with filename attribute
            error = FileNotFoundError(2, "No such file or directory")
            error.filename = file_path
            raise error

        with pytest.raises(QuackFileNotFoundError) as excinfo:
            function_with_file_not_found()

        assert file_path in str(excinfo.value)
        assert excinfo.value.path == file_path

    def test_permission_error_wrapping(self) -> None:
        """Test that PermissionError is converted to QuackPermissionError."""
        file_path = "/path/to/protected/file"

        @wrap_io_errors
        def function_with_permission_error() -> None:
            # Create a PermissionError with filename attribute
            error = PermissionError(13, "Permission denied")
            error.filename = file_path
            raise error

        with pytest.raises(QuackPermissionError) as excinfo:
            function_with_permission_error()

        assert file_path in str(excinfo.value)
        assert excinfo.value.path == file_path
        assert excinfo.value.operation == "access"  # Default operation

    def test_file_exists_wrapping(self) -> None:
        """Test that FileExistsError is converted to QuackFileExistsError."""
        file_path = "/path/to/existing/file"

        @wrap_io_errors
        def function_with_file_exists() -> None:
            # Create a FileExistsError with filename attribute
            error = FileExistsError(17, "File exists")
            error.filename = file_path
            raise error

        with pytest.raises(QuackFileExistsError) as excinfo:
            function_with_file_exists()

        assert file_path in str(excinfo.value)
        assert excinfo.value.path == file_path

    def test_general_os_error_wrapping(self) -> None:
        """Test that general OSError is converted to QuackIOError."""

        @wrap_io_errors
        def function_with_os_error() -> None:
            raise OSError("General OS error")

        with pytest.raises(QuackIOError) as excinfo:
            function_with_os_error()

        assert "General OS error" in str(excinfo.value)

    def test_unexpected_error_wrapping(self) -> None:
        """Test that unexpected exceptions are converted to QuackError."""

        @wrap_io_errors
        def function_with_type_error() -> None:
            raise TypeError("Type error")

        with pytest.raises(QuackError) as excinfo:
            function_with_type_error()

        assert "Type error" in str(excinfo.value)
        assert isinstance(excinfo.value.original_error, TypeError)
