# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_logging.py
# role: tests
# neighbors: __init__.py, mocks.py, test_bootstrap.py, test_config.py, test_context.py, test_error.py (+5 more)
# exports: TestDetermineEffectiveLevel, TestAddFileHandler, TestSetupLogging, TestLoggerFactory
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

"""
Tests for the CLI logging module.
"""

import logging
from unittest.mock import MagicMock, patch


from quack_core.config.models import QuackConfig
from quack_core.interfaces.cli.utils.logging import _determine_effective_level, \
    _add_file_handler, setup_logging


class TestDetermineEffectiveLevel:
    """Tests for _determine_effective_level function."""

    def test_with_debug_flag(self) -> None:
        """Test with debug flag set."""
        level = _determine_effective_level(None, True, False, None)
        assert level == "DEBUG"

    def test_with_quiet_flag(self) -> None:
        """Test with quiet flag set."""
        level = _determine_effective_level(None, False, True, None)
        assert level == "ERROR"

    def test_with_cli_log_level(self) -> None:
        """Test with CLI log level specified."""
        level = _determine_effective_level("WARNING", False, False, None)
        assert level == "WARNING"

    def test_with_config_level(self) -> None:
        """Test with config log level."""
        config = QuackConfig(logging={"level": "CRITICAL"})
        level = _determine_effective_level(None, False, False, config)
        assert level == "CRITICAL"

    def test_with_config_level_lowercase(self) -> None:
        """Test with config log level in lowercase."""
        config = QuackConfig(logging={"level": "critical"})
        level = _determine_effective_level(None, False, False, config)
        assert level == "CRITICAL"

    def test_with_invalid_config_level(self) -> None:
        """Test with invalid config log level."""
        config = QuackConfig(logging={"level": "INVALID"})
        level = _determine_effective_level(None, False, False, config)
        assert level == "INFO"  # Should default to INFO

    def test_default_level(self) -> None:
        """Test default log level."""
        level = _determine_effective_level(None, False, False, None)
        assert level == "INFO"

    def test_precedence(self) -> None:
        """Test precedence of log level determination."""
        # Debug flag should take highest precedence
        config = QuackConfig(logging={"level": "CRITICAL"})
        level = _determine_effective_level("WARNING", True, True, config)
        assert level == "DEBUG"

        # Quiet flag should take precedence over CLI level and config
        level = _determine_effective_level("WARNING", False, True, config)
        assert level == "ERROR"

        # CLI level should take precedence over config
        level = _determine_effective_level("WARNING", False, False, config)
        assert level == "WARNING"


class TestAddFileHandler:
    """Tests for _add_file_handler function."""

    def test_with_valid_log_file(self) -> None:
        """Test adding a file handler with a valid log file."""
        root_logger = logging.getLogger("test_add_file_handler")

        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        config = QuackConfig(logging={"file": "/path/to/logfile.log"})

        # Mock the fs service by patching the import where it's used
        with patch("quack_core.lib.fs.service.create_directory") as mock_create_dir:
            # Set up the success attribute on the result object
            result = MagicMock()
            result.success = True
            mock_create_dir.return_value = result

            with patch("logging.FileHandler") as mock_file_handler:
                mock_handler = MagicMock()
                mock_file_handler.return_value = mock_handler

                _add_file_handler(root_logger, config, logging.INFO)

                # Verify the directory was created with the correct path
                mock_create_dir.assert_called_once_with("/path/to", exist_ok=True)

                # Verify a file handler was created
                mock_file_handler.assert_called_once_with("/path/to/logfile.log")

                # Verify it was added to the logger
                mock_handler.setLevel.assert_called_once_with(logging.INFO)

    def test_with_directory_creation_failure(self) -> None:
        """Test handling failure to create log directory."""
        root_logger = logging.getLogger("test_dir_failure")

        # Clear handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        config = QuackConfig(logging={"file": "/path/to/logfile.log"})

        # Mock directory creation failure
        with patch("quack_core.lib.fs.service.create_directory") as mock_create_dir:
            # Set up a failed result
            result = MagicMock()
            result.success = False
            result.error = "Permission denied"
            mock_create_dir.return_value = result

            with patch("logging.FileHandler") as mock_file_handler:
                # Function should catch the exception and log warning
                _add_file_handler(root_logger, config, logging.INFO)

                # Verify no file handler was created
                mock_file_handler.assert_not_called()

    def test_with_no_log_file(self) -> None:
        """Test when no log file is specified."""
        root_logger = logging.getLogger("test_no_logfile")
        config = QuackConfig()  # No log file specified

        with patch("logging.FileHandler") as mock_file_handler:
            _add_file_handler(root_logger, config, logging.INFO)

            # Verify no file handler was created
            mock_file_handler.assert_not_called()

    def test_with_file_handler_exception(self) -> None:
        """Test handling exception when creating file handler."""
        root_logger = logging.getLogger("test_file_handler_exception")
        config = QuackConfig(logging={"file": "/path/to/logfile.log"})

        with patch("quack_core.lib.fs.service.create_directory") as mock_create_dir:
            # Set up a successful result
            result = MagicMock()
            result.success = True
            mock_create_dir.return_value = result

            with patch("logging.FileHandler") as mock_file_handler:
                mock_file_handler.side_effect = PermissionError("Permission denied")

                # Function should catch the exception
                _add_file_handler(root_logger, config, logging.INFO)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_basic_setup(self) -> None:
        """Test basic logging setup."""
        logger, factory = setup_logging()

        assert isinstance(logger, logging.Logger)
        assert callable(factory)
        assert logger.level == logging.INFO  # Default level

        # Verify we can create named loggers
        child_logger = factory("child")
        assert isinstance(child_logger, logging.Logger)
        assert child_logger.name == "quack.child"

    def test_with_debug_flag(self) -> None:
        """Test setup with debug flag."""
        logger, _ = setup_logging(debug=True)
        assert logger.level == logging.DEBUG

    def test_with_quiet_flag(self) -> None:
        """Test setup with quiet flag."""
        logger, _ = setup_logging(quiet=True)
        assert logger.level == logging.ERROR

    def test_with_explicit_level(self) -> None:
        """Test setup with explicit log level."""
        logger, _ = setup_logging(log_level="WARNING")
        assert logger.level == logging.WARNING

    def test_with_config(self) -> None:
        """Test setup with configuration."""
        config = QuackConfig(
            logging={"level": "CRITICAL", "file": "/path/to/logfile.log"}
        )

        with patch("quack_core.interfaces.cli.utils.logging._add_file_handler") as mock_add_file:
            logger, _ = setup_logging(config=config)

            assert logger.level == logging.CRITICAL
            mock_add_file.assert_called_once()

    def test_with_custom_logger_name(self) -> None:
        """Test setup with custom logger name."""
        logger, factory = setup_logging(logger_name="custom")

        assert logger.name == "custom"

        # Test factory creates loggers with correct prefix
        child_logger = factory("child")
        assert child_logger.name == "custom.child"

    def test_handlers_configuration(self) -> None:
        """Test handlers are properly configured."""
        with patch("logging.StreamHandler") as mock_stream_handler:
            mock_handler = MagicMock()
            mock_stream_handler.return_value = mock_handler

            logger, _ = setup_logging()

            # Verify a console handler was added
            mock_stream_handler.assert_called_once()
            mock_handler.setFormatter.assert_called_once()
            mock_handler.setLevel.assert_called_once()

    def test_debug_formatter(self) -> None:
        """Test that debug mode uses a different formatter."""
        with patch("logging.Formatter") as mock_formatter:
            logger, _ = setup_logging(debug=True)

            # Should create a formatter with more details for debug mode
            format_str = mock_formatter.call_args[0][0]
            assert "%(name)s" in format_str
            assert "%(asctime)s" in format_str
            assert "%(levelname)s" in format_str

    def test_non_debug_formatter(self) -> None:
        """Test formatter in non-debug mode."""
        with patch("logging.Formatter") as mock_formatter:
            logger, _ = setup_logging(debug=False)

            # Should create a simpler formatter for regular mode
            format_str = mock_formatter.call_args[0][0]
            assert format_str == "%(levelname)s: %(message)s"

    def test_logger_factory(self) -> None:
        """Test the logger factory."""
        _, factory = setup_logging(logger_name="factory_test")

        # Create loggers with different names
        logger1 = factory("module1")
        logger2 = factory("module2")

        assert logger1.name == "factory_test.module1"
        assert logger2.name == "factory_test.module2"

        # Verify they inherit the root logger's level
        root_logger = logging.getLogger("factory_test")
        assert logger1.level == root_logger.level
        assert logger2.level == root_logger.level


class TestLoggerFactory:
    """Tests for the LoggerFactory protocol."""

    def test_protocol_compliance(self) -> None:
        """Test that functions follow the LoggerFactory protocol."""

        # Create a function that matches the protocol
        def factory(name: str) -> logging.Logger:
            return logging.getLogger(name)

        # There's no direct way to check protocol compliance at runtime,
        # but we can verify it has the expected signature and behavior
        assert callable(factory)
        result = factory("test")
        assert isinstance(result, logging.Logger)

        # The setup_logging function returns a factory that should comply
        _, factory_from_setup = setup_logging()
        assert callable(factory_from_setup)
        result = factory_from_setup("test")
        assert isinstance(result, logging.Logger)
