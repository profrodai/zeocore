# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_bootstrap.py
# role: tests
# neighbors: __init__.py, mocks.py, test_config.py, test_context.py, test_error.py, test_formatting.py (+5 more)
# exports: TestInitCliEnv, TestFromCliOptions
# git_branch: refactor/toolkitWorkflow
# git_commit: e4fa88d
# === QV-LLM:END ===

"""
Tests for the CLI bootstrap module.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from quack_core.interfaces.cli.legacy.boostrap import from_cli_options, init_cli_env
from quack_core.interfaces.cli.legacy.context import QuackContext
from quack_core.interfaces.cli.utils.options import CliOptions
from quack_core.lib.errors import QuackError

from .mocks import (
    MockConfig,
    create_mock_logger,
    patch_common_dependencies,
)


class TestInitCliEnv:
    """Tests for init_cli_env function."""

    @patch_common_dependencies
    def test_successful_initialization(
        self, mock_find_root, mock_load_config, mock_setup_logging
    ):
        """Test successful initialization of CLI environment."""
        # Customize mocks for this test
        mock_find_root.return_value = "/project/root"

        # Create a mock config that will respond to attribute changes
        mock_config = MockConfig()
        mock_load_config.return_value = mock_config

        # Set up logger mocks
        mock_logger = create_mock_logger()
        mock_get_logger = MagicMock()
        mock_setup_logging.return_value = (mock_logger, mock_get_logger)

        # Create a mock QuackContext to return
        mock_context = MagicMock(spec=QuackContext)

        # Patch the QuackContext constructor to avoid validation errors
        with patch("quack_core.interfaces.cli.legacy.boostrap.QuackContext", return_value=mock_context):
            # Set environment for test
            with patch.dict(os.environ, {"QUACK_ENV": "development"}):
                # Call the function under test
                context = init_cli_env()

                # Verify mocks were called correctly
                mock_find_root.assert_called_once()
                mock_load_config.assert_called_once_with(None, None, None)
                mock_setup_logging.assert_called_once_with(
                    None, False, False, mock_config, "quack"
                )

                # Now verify the context attributes
                assert context is mock_context

    @patch("quack_core.interfaces.cli.legacy.boostrap.setup_logging")
    @patch("quack_core.interfaces.cli.legacy.boostrap.load_config")
    @patch("quack_core.interfaces.cli.legacy.boostrap.find_project_root")
    def test_with_explicit_parameters(
        self, mock_find_root, mock_load_config, mock_setup_logging
    ):
        """Test initialization with explicit parameters."""
        # Customize mocks for this test
        mock_find_root.return_value = "/custom/base/dir"

        # Create a mock config manually rather than using the decorator
        mock_config = MockConfig()
        mock_load_config.return_value = mock_config

        # Set up logger mocks
        mock_logger = create_mock_logger()
        mock_get_logger = MagicMock()
        mock_setup_logging.return_value = (mock_logger, mock_get_logger)

        # Create a mock QuackContext to return
        mock_context = MagicMock(spec=QuackContext)

        # Patch the QuackContext constructor to avoid validation errors
        with patch("quack_core.interfaces.cli.legacy.boostrap.QuackContext", return_value=mock_context):
            # Call with explicit parameters
            context = init_cli_env(
                config_path="/path/to/config.yaml",
                log_level="DEBUG",
                debug=True,
                verbose=True,
                quiet=True,
                environment="test",
                base_dir="/custom/base/dir",
                cli_args={"key": "value"},
                app_name="test_app",
            )

            # Verify the parameters were passed correctly
            mock_load_config.assert_called_once_with(
                "/path/to/config.yaml", {"key": "value"}, "test"
            )
            mock_setup_logging.assert_called_once_with(
                "DEBUG", True, True, mock_config, "test_app"
            )

            # Verify the context was returned
            assert context is mock_context

            # Verify debug and verbose flags were set on the config
            assert mock_config.general.debug is True
            assert mock_config.general.verbose is True

    @patch_common_dependencies
    def test_with_debug_flag(
        self, mock_find_root, mock_load_config, mock_setup_logging
    ):
        """Test that debug flag sets config.general.debug."""
        # Create a mock config
        mock_config = MockConfig()
        mock_load_config.return_value = mock_config

        # Set up logger mocks
        mock_logger = create_mock_logger()
        mock_get_logger = MagicMock()
        mock_setup_logging.return_value = (mock_logger, mock_get_logger)

        # Create a mock QuackContext to return
        mock_context = MagicMock(spec=QuackContext)

        # Patch the QuackContext constructor to avoid validation errors
        with patch("quack_core.interfaces.cli.legacy.boostrap.QuackContext", return_value=mock_context):
            # Call with debug=True
            init_cli_env(debug=True)

            # Verify debug was set in config
            assert mock_config.general.debug is True

    @patch_common_dependencies
    def test_with_verbose_flag(
        self, mock_find_root, mock_load_config, mock_setup_logging
    ):
        """Test that verbose flag sets config.general.verbose."""
        # Create a mock config
        mock_config = MockConfig()
        mock_load_config.return_value = mock_config

        # Set up logger mocks
        mock_logger = create_mock_logger()
        mock_get_logger = MagicMock()
        mock_setup_logging.return_value = (mock_logger, mock_get_logger)

        # Create a mock QuackContext to return
        mock_context = MagicMock(spec=QuackContext)

        # Patch the QuackContext constructor to avoid validation errors
        with patch("quack_core.interfaces.cli.legacy.boostrap.QuackContext", return_value=mock_context):
            # Call with verbose=True
            init_cli_env(verbose=True)

            # Verify verbose was set in config
            assert mock_config.general.verbose is True

    def test_error_handling(self):
        """Test error handling during initialization."""
        # Test QuackError is re-raised
        with patch(
            "quack_core.interfaces.cli.legacy.boostrap.find_project_root",
            side_effect=QuackError("Project root error"),
        ):
            with patch("logging.error") as mock_error_logger:
                with pytest.raises(QuackError) as excinfo:
                    init_cli_env()

                # Verify the error message
                assert "Project root error" in str(excinfo.value)
                mock_error_logger.assert_called_once()

        # Test other exceptions are wrapped in QuackError
        with patch(
            "quack_core.interfaces.cli.legacy.boostrap.find_project_root",
            side_effect=ValueError("Unexpected error"),
        ):
            with patch("logging.error") as mock_error_logger:
                with pytest.raises(QuackError) as excinfo:
                    init_cli_env()

                # Verify error wrapping
                assert "Unexpected error initializing CLI environment" in str(
                    excinfo.value
                )
                assert "Unexpected error" in str(excinfo.value)
                mock_error_logger.assert_called_once()


class TestFromCliOptions:
    """Tests for from_cli_options function."""

    @patch("quack_core.interfaces.cli.legacy.boostrap.init_cli_env")
    def test_from_cli_options(self, mock_init_cli_env):
        """Test creating a context from CliOptions."""
        # Set up mocks
        mock_context = MagicMock(spec=QuackContext)
        mock_init_cli_env.return_value = mock_context

        # Create options
        options = CliOptions(
            config_path="/path/to/config.yaml",
            log_level="DEBUG",
            debug=True,
            verbose=True,
            quiet=False,
            environment="test",
            base_dir="/custom/base/dir",
            no_color=True,
        )

        # Call the function under test
        context = from_cli_options(options, {"key": "value"}, "test_app")

        # Verify init_cli_env was called with the right parameters
        mock_init_cli_env.assert_called_once_with(
            config_path="/path/to/config.yaml",
            log_level="DEBUG",
            debug=True,
            verbose=True,
            quiet=False,
            environment="test",
            base_dir="/custom/base/dir",
            cli_args={"key": "value"},
            app_name="test_app",
        )

        # Verify the function returns the context from init_cli_env
        assert context is mock_context
