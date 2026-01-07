# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_config.py
# role: tests
# neighbors: __init__.py, mocks.py, test_bootstrap.py, test_context.py, test_error.py, test_formatting.py (+5 more)
# exports: TestFindProjectRoot, TestLoadConfig, TestMergeCliOverrides
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Tests for the CLI config module.
"""

import os
from unittest.mock import patch

import pytest
from quack_core.config.models import QuackConfig
from quack_core.interfaces.cli.legacy.config import (
    _merge_cli_overrides,
    find_project_root,
    load_config,
)
from quack_core.lib.errors import QuackConfigurationError, QuackFileNotFoundError

from .mocks import MockConfig


class TestFindProjectRoot:
    """Tests for find_project_root function."""

    def test_with_resolver(self):
        """Test using the path resolver."""
        # Patch the paths.service that's imported at the module level
        with patch(
            "quack_core.interfaces.cli.legacy.config.paths.get_project_root"
        ) as mock_get_root:
            # Set up mock to return a specific path string
            mock_get_root.return_value = "/project/root"

            # Mock os.getcwd() to avoid fallback issues
            with patch("os.getcwd", return_value="/some/other/path"):
                # Call the function under test
                result = find_project_root()

                # Verify the result
                assert result == "/project/root"
                mock_get_root.assert_called_once()

    def test_with_exception(self):
        """Test handling exceptions from resolver."""
        # Test various exceptions that should be caught
        exceptions = [
            FileNotFoundError("File not found"),
            PermissionError("Permission denied"),
            ValueError("Invalid value"),
            NotImplementedError("Not implemented"),
        ]

        for exception in exceptions:
            with patch(
                "quack_core.interfaces.cli.legacy.config.paths.get_project_root"
            ) as mock_get_root:
                mock_get_root.side_effect = exception

                # Mock os.getcwd() for deterministic test results
                with patch("os.getcwd", return_value="/fallback/path"):
                    # Call the function under test
                    result = find_project_root()

                    # Should fall back to cwd
                    assert result == "/fallback/path"

        # Special handling for QuackFileNotFoundError
        with patch(
            "quack_core.interfaces.cli.legacy.config.paths.get_project_root"
        ) as mock_get_root:
            mock_get_root.side_effect = QuackFileNotFoundError(
                "unknown", "File not found"
            )

            # Mock os.getcwd() for deterministic test results
            with patch("os.getcwd", return_value="/fallback/path"):
                # Call the function under test
                result = find_project_root()

                # Should fall back to cwd
                assert result == "/fallback/path"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_with_explicit_path(self):
        """Test loading with an explicit config path."""
        # Patch the internal helper function directly
        with patch("quack_core.interfaces.cli.legacy.config._get_core_config") as mock_get_core_config:
            # Set up mock
            mock_config = MockConfig()
            mock_get_core_config.return_value = mock_config

            # Patch utility functions
            with patch(
                "quack_core.interfaces.cli.legacy.config.normalize_paths", return_value=mock_config
            ):
                with patch(
                    "quack_core.interfaces.cli.legacy.config.load_env_config", return_value=mock_config
                ):
                    # Override _is_test_path for this test to return False
                    with patch(
                        "quack_core.interfaces.cli.legacy.config._is_test_path", return_value=False
                    ):
                        # Call the function under test
                        config = load_config("/path/to/config.yaml")

                        # Verify result and mock calls
                        assert config is mock_config
                        mock_get_core_config.assert_called_once_with(
                            "/path/to/config.yaml"
                        )

    def test_load_with_cli_overrides(self):
        """Test loading with CLI argument overrides."""
        with patch("quack_core.interfaces.cli.legacy.config._get_core_config") as mock_get_core_config:
            with patch("quack_core.interfaces.cli.legacy.config._merge_cli_overrides") as mock_merge:
                # Set up mocks
                mock_config = MockConfig()
                mock_merged_config = MockConfig()
                mock_get_core_config.return_value = mock_config
                mock_merge.return_value = mock_merged_config

                # Patch normalize_paths to return the merged mock
                with patch(
                    "quack_core.interfaces.cli.legacy.config.normalize_paths",
                    return_value=mock_merged_config,
                ):
                    with patch(
                        "quack_core.interfaces.cli.legacy.config.load_env_config", return_value=mock_config
                    ):
                        # Call with CLI overrides
                        cli_args = {"debug": True, "log_level": "DEBUG"}
                        config = load_config(cli_overrides=cli_args)

                        # Verify _merge_cli_overrides was called with the right arguments
                        mock_merge.assert_called_once_with(mock_config, cli_args)
                        assert config is mock_merged_config

    def test_load_with_environment(self):
        """Test loading with environment override."""
        with patch("quack_core.interfaces.cli.legacy.config._get_core_config") as mock_get_core_config:
            # Set up mock
            mock_config = MockConfig()
            mock_get_core_config.return_value = mock_config

            # Patch normalize_paths to return the mock
            with patch(
                "quack_core.interfaces.cli.legacy.config.normalize_paths", return_value=mock_config
            ):
                with patch(
                    "quack_core.interfaces.cli.legacy.config.load_env_config", return_value=mock_config
                ):
                    # Call with environment
                    with patch.dict("os.environ", {}, clear=True):
                        config = load_config(environment="production")

                        # Verify environment was set and passed
                        assert os.environ.get("QUACK_ENV") == "production"
                        mock_get_core_config.assert_called_once_with(None)
                        assert config is mock_config

    def test_load_with_config_error(self):
        """Test handling configuration errors."""
        with patch("quack_core.interfaces.cli.legacy.config._get_core_config") as mock_get_core_config:
            # Set up mock to raise error
            mock_get_core_config.side_effect = QuackConfigurationError("Config error")

            # Force non-test mode to ensure error is re-raised
            with patch("quack_core.interfaces.cli.legacy.config._is_test_path", return_value=False):
                with patch("quack_core.interfaces.cli.legacy.config.is_test", False):
                    # Test when config_path is given but raises an error
                    with pytest.raises(QuackConfigurationError):
                        load_config("/path/to/config.yaml")

            # Reset the mock for the next test
            mock_get_core_config.reset_mock()
            mock_get_core_config.side_effect = QuackConfigurationError("Config error")

            # Test when in test mode - should not raise but return default config
            mock_default_config = MockConfig()
            with patch(
                "quack_core.config.models.QuackConfig", return_value=mock_default_config
            ):
                with patch(
                    "quack_core.interfaces.cli.legacy.config.normalize_paths",
                    return_value=mock_default_config,
                ):
                    with patch(
                        "quack_core.interfaces.cli.legacy.config.load_env_config",
                        return_value=mock_default_config,
                    ):
                        with patch("quack_core.interfaces.cli.legacy.config.is_test", True):
                            config = load_config()

                            # Should return the default config
                            assert isinstance(config, MockConfig)

    def test_normalize_paths(self):
        """Test that paths are normalized in the configuration."""
        with patch("quack_core.interfaces.cli.legacy.config._get_core_config") as mock_get_core_config:
            with patch("quack_core.interfaces.cli.legacy.config.normalize_paths") as mock_normalize:
                # Set up mocks
                mock_config = MockConfig()
                mock_normalized_config = MockConfig()
                mock_get_core_config.return_value = mock_config
                mock_normalize.return_value = mock_normalized_config

                # Patch load_env_config to return the same mock_config
                with patch(
                    "quack_core.interfaces.cli.legacy.config.load_env_config", return_value=mock_config
                ):
                    # Call the function
                    config = load_config()

                    # Verify normalize_paths was called
                    mock_normalize.assert_called_once_with(mock_config)
                    assert config is mock_normalized_config


class TestMergeCliOverrides:
    """Tests for _merge_cli_overrides function."""

    def test_merge_simple_overrides(self):
        """Test merging simple CLI overrides."""
        # Create a base config
        config = QuackConfig()

        # Create CLI overrides
        cli_overrides = {
            "debug": True,
            "log_level": "DEBUG",
            "output_dir": "/output",
        }

        # Mock dependencies
        with patch("quack_core.config.loader.merge_configs") as mock_merge:
            # Set up mock for merge_configs
            mock_merged_config = MockConfig()
            mock_merge.return_value = mock_merged_config

            # Call the function under test
            result = _merge_cli_overrides(config, cli_overrides)

            # Verify merge_configs was called with the right overrides
            mock_merge.assert_called_once()

            # Verify the arguments passed to merge_configs
            call_args = mock_merge.call_args[0]
            assert call_args[0] is config  # First arg should be original config

            # Verify override dict contains expected keys and values
            override_dict = call_args[1]  # Second arg should be override dict
            for key, value in cli_overrides.items():
                assert key in override_dict
                assert override_dict[key] == value

            # Verify function returns merged config
            assert result is mock_merged_config

    def test_merge_with_nested_paths(self):
        """Test merging CLI overrides with nested paths."""
        # Create a base config
        config = QuackConfig()

        # Create CLI overrides with dot notation paths
        cli_overrides = {
            "general.debug": True,
            "logging.level": "DEBUG",
            "paths.output_dir": "/output",
        }

        # Mock dependencies
        with patch("quack_core.config.loader.merge_configs") as mock_merge:
            # Set up mock for merge_configs
            mock_merged_config = MockConfig()
            mock_merge.return_value = mock_merged_config

            # Call the function under test
            result = _merge_cli_overrides(config, cli_overrides)

            # Verify merge_configs was called
            mock_merge.assert_called_once()

            # Check the nested structure was created correctly
            call_args = mock_merge.call_args[0]
            assert call_args[0] is config

            # Check the nested dict structure
            override_dict = call_args[1]
            assert "general" in override_dict
            assert override_dict["general"]["debug"] is True
            assert "logging" in override_dict
            assert override_dict["logging"]["level"] == "DEBUG"
            assert "paths" in override_dict
            assert override_dict["paths"]["output_dir"] == "/output"

            # Verify function returns merged config
            assert result is mock_merged_config

    def test_merge_with_ignored_keys(self):
        """Test that certain keys are ignored during merge."""
        # Create a base config
        config = QuackConfig()

        # Create CLI overrides with some keys that should be ignored
        cli_overrides = {
            "config": "/path/to/config.yaml",  # Should be ignored
            "help": True,  # Should be ignored
            "version": True,  # Should be ignored
            "debug": True,  # Should NOT be ignored
        }

        # Mock dependencies
        with patch("quack_core.config.loader.merge_configs") as mock_merge:
            # Set up mock for merge_configs
            mock_merged_config = MockConfig()
            mock_merge.return_value = mock_merged_config

            # Call the function under test
            result = _merge_cli_overrides(config, cli_overrides)

            # Verify merge_configs was called
            mock_merge.assert_called_once()

            # Check that ignored keys are not included
            call_args = mock_merge.call_args[0]
            override_dict = call_args[1]

            # Non-ignored key should be present
            assert "debug" in override_dict
            assert override_dict["debug"] is True

            # Ignored keys should not be present
            assert "config" not in override_dict
            assert "help" not in override_dict
            assert "version" not in override_dict

            # Verify function returns merged config
            assert result is mock_merged_config
