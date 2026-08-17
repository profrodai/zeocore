"""
Tests for ZeoCore error classes and decorators.
"""

from pathlib import Path
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from zeo_core.core.errors import (
    ZeoBaseAuthError,
    ZeoConfigurationError,
    ZeoError,
    ZeoFileExistsError,
    ZeoFileNotFoundError,
    ZeoFormatError,
    ZeoIOError,
    ZeoPermissionError,
    ZeoPluginError,
    ZeoValidationError,
    wrap_io_errors,
)


class TestZeoError:
    """Tests for the base ZeoError class."""

    def test_basic_functionality(self) -> None:
        """Test creating a ZeoError with just a message."""
        error = ZeoError("Test error message")

        assert str(error) == "Test error message"
        assert error.context == {}
        assert error.original_error is None

    @given(st.text(min_size=1), st.dictionaries(st.text(), st.text()))
    def test_with_context(self, message: str, context: dict[str, str]) -> None:
        """Test ZeoError with a message and context dictionary."""
        # dict[str, str] deliberately narrower than ZeoError's own
        # dict[str, object] parameter -- this property test's whole point is
        # exercising arbitrary string-valued dicts, and dict's invariance
        # means it isn't assignable to dict[str, object] even though
        # ZeoError only ever reads context (never mutates it). Cast
        # reflects that read-only variance gap, not a real type mismatch.
        error = ZeoError(message, context=cast(dict[str, object], context))

        assert error.context == context
        # Check that context info is included in the string representation
        if context:
            assert all(key in str(error) for key in context.keys())

    def test_with_original_error(self) -> None:
        """Test ZeoError with an original exception."""
        original = ValueError("Original error")
        error = ZeoError("Wrapped error", original_error=original)

        assert error.original_error is original
        assert "Wrapped error" in str(error)

    def test_exception_chaining(self) -> None:
        """Test that exception chaining works correctly."""
        original = ValueError("Original error")

        try:
            try:
                raise original
            except ValueError as e:
                raise ZeoError("Wrapped error", original_error=e) from e
        except ZeoError as e:
            assert e.__cause__ is original
            assert e.original_error is original


class TestZeoIOError:
    """Tests for ZeoIOError."""

    def test_with_string_path(self) -> None:
        """Test creating a ZeoIOError with a string path."""
        error = ZeoIOError("IO error message", "/path/to/file")

        assert error.path == "/path/to/file"
        assert "path='/path/to/file'" in str(error)

    def test_with_path_object(self) -> None:
        """Test creating a ZeoIOError with a Path object."""
        path = Path("/path/to/file")
        error = ZeoIOError("IO error message", path)

        assert error.path == str(path)
        assert "path='/path/to/file'" in str(error)


class TestSpecificErrors:
    """Tests for specific error subclasses."""

    def test_file_not_found_error(self) -> None:
        """Test ZeoFileNotFoundError."""
        error = ZeoFileNotFoundError("/path/to/missing/file")

        assert "File or directory not found" in str(error)
        assert error.path == "/path/to/missing/file"

        # Test with custom message
        custom_error = ZeoFileNotFoundError("/path/to/file", "Custom message")
        assert "Custom message" in str(custom_error)

    def test_permission_error(self) -> None:
        """Test ZeoPermissionError."""
        error = ZeoPermissionError("/path/to/file", "read")

        assert "Permission denied for read operation" in str(error)
        assert error.path == "/path/to/file"
        assert error.operation == "read"

    def test_file_exists_error(self) -> None:
        """Test ZeoFileExistsError."""
        error = ZeoFileExistsError("/path/to/existing/file")

        assert "File or directory already exists" in str(error)
        assert error.path == "/path/to/existing/file"

    def test_validation_error(self) -> None:
        """Test ZeoValidationError."""
        errors = {"field1": ["Value too short"], "field2": ["Invalid format"]}
        error = ZeoValidationError("Validation failed", "/path/to/file", errors)

        assert "Validation failed" in str(error)
        assert error.path == "/path/to/file"
        assert error.errors == errors

    def test_format_error(self) -> None:
        """Test ZeoFormatError."""
        error = ZeoFormatError("/path/to/file", "JSON")

        assert "Invalid JSON format" in str(error)
        assert error.path == "/path/to/file"
        assert error.format_name == "JSON"

    def test_configuration_error(self) -> None:
        """Test ZeoConfigurationError."""
        error = ZeoConfigurationError(
            "Config error", "/path/to/config.yaml", "database.url"
        )

        assert "Config error" in str(error)
        assert error.config_path == "/path/to/config.yaml"
        assert error.config_key == "database.url"

    def test_plugin_error(self) -> None:
        """Test ZeoPluginError."""
        error = ZeoPluginError("Plugin error", "test_plugin", "/path/to/plugin.py")

        assert "Plugin error" in str(error)
        assert error.plugin_name == "test_plugin"
        assert error.plugin_path == "/path/to/plugin.py"

    def test_authentication_error(self) -> None:
        """Test ZeoAuthenticationError."""
        error = ZeoBaseAuthError(
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
        """Test that ValueError is converted to ZeoValidationError."""

        @wrap_io_errors
        def function_with_value_error() -> None:
            raise ValueError("Invalid value")

        with pytest.raises(ZeoValidationError) as excinfo:
            function_with_value_error()

        assert "Invalid value" in str(excinfo.value)
        assert isinstance(excinfo.value.original_error, ValueError)

    def test_file_not_found_wrapping(self) -> None:
        """Test that FileNotFoundError is converted to ZeoFileNotFoundError."""
        file_path = "/path/to/nonexistent/file"

        @wrap_io_errors
        def function_with_file_not_found() -> None:
            # Create a FileNotFoundError with filename attribute
            error = FileNotFoundError(2, "No such file or directory")
            error.filename = file_path
            raise error

        with pytest.raises(ZeoFileNotFoundError) as excinfo:
            function_with_file_not_found()

        assert file_path in str(excinfo.value)
        assert excinfo.value.path == file_path

    def test_permission_error_wrapping(self) -> None:
        """Test that PermissionError is converted to ZeoPermissionError."""
        file_path = "/path/to/protected/file"

        @wrap_io_errors
        def function_with_permission_error() -> None:
            # Create a PermissionError with filename attribute
            error = PermissionError(13, "Permission denied")
            error.filename = file_path
            raise error

        with pytest.raises(ZeoPermissionError) as excinfo:
            function_with_permission_error()

        assert file_path in str(excinfo.value)
        assert excinfo.value.path == file_path
        assert excinfo.value.operation == "access"  # Default operation

    def test_file_exists_wrapping(self) -> None:
        """Test that FileExistsError is converted to ZeoFileExistsError."""
        file_path = "/path/to/existing/file"

        @wrap_io_errors
        def function_with_file_exists() -> None:
            # Create a FileExistsError with filename attribute
            error = FileExistsError(17, "File exists")
            error.filename = file_path
            raise error

        with pytest.raises(ZeoFileExistsError) as excinfo:
            function_with_file_exists()

        assert file_path in str(excinfo.value)
        assert excinfo.value.path == file_path

    def test_general_os_error_wrapping(self) -> None:
        """Test that general OSError is converted to ZeoIOError."""

        @wrap_io_errors
        def function_with_os_error() -> None:
            raise OSError("General OS error")

        with pytest.raises(ZeoIOError) as excinfo:
            function_with_os_error()

        assert "General OS error" in str(excinfo.value)

    def test_unexpected_error_wrapping(self) -> None:
        """Test that unexpected exceptions are converted to ZeoError."""

        @wrap_io_errors
        def function_with_type_error() -> None:
            raise TypeError("Type error")

        with pytest.raises(ZeoError) as excinfo:
            function_with_type_error()

        assert "Type error" in str(excinfo.value)
        assert isinstance(excinfo.value.original_error, TypeError)
