# quack-core/tests/test_integrations/core/base/test_config_provider_discovery.py
"""
Tests for the config discovery functionality in BaseConfigProvider.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from quack_core.errors import QuackConfigurationError, QuackFileNotFoundError

from .config_provider_impl import (
    MockConfigProvider,
)


class TestBaseConfigProviderDiscovery:
    """Tests for config discovery functionality in BaseConfigProvider."""

    def test_load_config_discover(self) -> None:
        """Test loading configuration by discovering the file."""
        provider = MockConfigProvider()

        # Test with environment variable
        with patch.dict(os.environ, {"QUACK_TEST_CONFIG_CONFIG": "/env/config.yaml"}):
            with patch.object(provider, "_find_config_file") as mock_find:
                mock_find.return_value = "/env/config.yaml"

                with patch(
                        "quack_core.fs.service.standalone.get_file_info") as mock_info:
                    mock_info.return_value.success = True
                    mock_info.return_value.exists = True

                    with patch(
                            "quack_core.fs.service.standalone.read_yaml") as mock_read:
                        mock_read.return_value.success = True
                        mock_read.return_value.data = {
                            "test_section": {"test_key": "env_value"}
                        }

                        result = provider.load_config()
                        assert result.success is True
                        assert result.content == {"test_key": "env_value"}
                        assert result.config_path == "/env/config.yaml"

        # Test with default locations
        with patch.object(provider, "_find_config_file") as mock_find:
            mock_find.return_value = "/default/config.yaml"

            with patch("quack_core.fs.service.standalone.get_file_info") as mock_info:
                mock_info.return_value.success = True
                mock_info.return_value.exists = True

                with patch("quack_core.fs.service.standalone.read_yaml") as mock_read:
                    mock_read.return_value.success = True
                    mock_read.return_value.data = {
                        "test_section": {"test_key": "default_value"}
                    }

                    result = provider.load_config()
                    assert result.success is True
                    assert result.content == {"test_key": "default_value"}
                    assert result.config_path == "/default/config.yaml"

        # Test when no config file is found
        with patch.object(provider, "_find_config_file") as mock_find:
            mock_find.return_value = None

            with pytest.raises(QuackConfigurationError):
                provider.load_config()

    def test_find_config_file(self) -> None:
        """Test finding a configuration file in standard locations."""
        provider = MockConfigProvider()

        # Test with environment variable
        with patch.dict(os.environ, {"QUACK_TEST_CONFIG_CONFIG": "/env/config.yaml"}):
            with patch("quack_core.fs.service.standalone.expand_user_vars") as mock_expand:
                mock_expand.return_value = Path("/env/config.yaml")

                with patch(
                        "quack_core.fs.service.standalone.get_file_info") as mock_file_info:
                    mock_file_info.return_value.success = True
                    mock_file_info.return_value.exists = True

                    # Patch paths.service to avoid using get_project_root which is missing
                    with patch(
                            "quack_core.paths.service.get_project_root",
                            create=True) as mock_get_root:
                        # Just ensure it doesn't get called here
                        result = provider._find_config_file()
                        assert result == "/env/config.yaml"
                        mock_expand.assert_called_once_with("/env/config.yaml")
                        mock_file_info.assert_called_once_with(Path("/env/config.yaml"))
                        mock_get_root.assert_not_called()

        # Test with default locations
        with patch("quack_core.paths.service.get_project_root",
                   create=True) as mock_get_root:
            mock_get_root.side_effect = QuackFileNotFoundError("mock error")

            with patch(
                    "quack_core.fs.service.standalone.get_file_info") as mock_file_info:
                def side_effect(path):
                    mock_result = MagicMock()
                    mock_result.success = True
                    mock_result.exists = str(path) == "/default/config.yaml"
                    return mock_result

                mock_file_info.side_effect = side_effect

                with patch("quack_core.fs.service.standalone.expand_user_vars") as mock_expand:
                    mock_expand.side_effect = (
                        lambda path: Path("/default") / Path(path).name
                    )

                    with patch.object(
                            provider,
                            "DEFAULT_CONFIG_LOCATIONS",
                            ["config.yaml", "quack_config.yaml"],
                    ):
                        result = provider._find_config_file()
                        assert result == "/default/config.yaml"

        # Test with project root detection
        with patch("quack_core.paths.service.get_project_root",
                   create=True) as mock_get_root:
            mock_get_root.return_value = Path("/project")

            with patch("quack_core.fs.service.standalone.join_path") as mock_join:
                mock_join.return_value = Path("/project/quack_config.yaml")

                with patch(
                        "quack_core.fs.service.standalone.get_file_info") as mock_file_info:
                    mock_file_info.return_value.success = True
                    mock_file_info.return_value.exists = True

                    with patch("quack_core.fs.service.standalone.expand_user_vars") as mock_expand:
                        mock_expand.return_value = Path("/project/quack_config.yaml")

                        result = provider._find_config_file()
                        assert result == "/project/quack_config.yaml"

        # Test when no config file can be found
        with patch("quack_core.paths.service.get_project_root",
                   create=True) as mock_get_root:
            mock_get_root.side_effect = QuackFileNotFoundError("/nonexistent")

            with patch(
                    "quack_core.fs.service.standalone.get_file_info") as mock_file_info:
                mock_file_info.return_value.success = True
                mock_file_info.return_value.exists = False

                with patch("quack_core.fs.service.standalone.expand_user_vars") as mock_expand:
                    mock_expand.side_effect = lambda x: x

                    result = provider._find_config_file()
                    assert result is None

    def test_extract_config(self) -> None:
        """Test extracting integration-specific configuration."""
        provider = MockConfigProvider()

        # Test with matching section
        config_data = {"test_section": {"test_key": "test_value"}}
        result = provider._extract_config(config_data)
        assert result == {"test_key": "test_value"}

        # Test with missing section
        config_data = {"other_section": {}}
        result = provider._extract_config(config_data)
        assert result == {}

    def test_resolve_path(self) -> None:
        """Test resolving a path relative to the project root."""
        provider = MockConfigProvider()

        # Test with fs service standalone resolver
        with patch(
                "quack_core.fs.service.standalone.resolve_path"
        ) as mock_resolve:
            mock_resolve.return_value = "/resolved/path"

            result = provider._resolve_path("relative/path")
            assert result == "/resolved/path"
            mock_resolve.assert_called_once_with("relative/path")

        # Test with resolver exception
        with patch(
                "quack_core.fs.service.standalone.resolve_path"
        ) as mock_resolve:
            mock_resolve.side_effect = Exception("Test error")

            result = provider._resolve_path("relative/path")
            # The modified implementation now just returns the original path in case of exception
            assert result == "relative/path"
