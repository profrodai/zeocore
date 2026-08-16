# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/base/test_config_provider.py
# === QV-LLM:END ===

"""
Tests for the BaseConfigProvider class.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from quack_core.core.errors import QuackConfigurationError
from quack_core.integrations.core.base import BaseConfigProvider

from .config_provider_impl import (
    MockConfigProvider,
)


class TestBaseConfigProvider:
    """Tests for the BaseConfigProvider class."""

    def test_init(self) -> None:
        """Test initializing the config provider."""
        provider = MockConfigProvider()
        assert provider.name == "test_config"

    def test_abstract_methods(self) -> None:
        """Test that abstract methods must be implemented."""
        # Attempt to create a class without implementing all abstract methods
        with pytest.raises(TypeError):

            class InvalidProvider(BaseConfigProvider):
                @property
                def name(self) -> str:
                    return "invalid"

            # Deliberately incomplete (missing get_default_config/validate_config)
            # -- this test's whole point is exercising Python's abstract-class
            # enforcement at instantiation time (see pytest.raises above).
            InvalidProvider()  # type: ignore[abstract]  # This should raise TypeError

    def test_load_config_with_path(self, temp_dir: Path) -> None:
        """Test loading configuration with an explicit path."""
        # Create a config file
        config_file = temp_dir / "test_config.yaml"
        config_file.write_text("""
        test_section:
          test_key: test_value
        """)

        provider = MockConfigProvider()

        # Test successful load
        with patch("quack_core.core.fs.service.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True

            with patch("quack_core.core.fs.service.standalone.read_yaml") as mock_read:
                mock_read.return_value.success = True
                mock_read.return_value.data = {
                    "test_section": {"test_key": "test_value"}
                }

                result = provider.load_config(str(config_file))
                assert result.success is True
                assert result.content == {"test_key": "test_value"}
                assert result.config_path == str(config_file)

        # Test file not found
        with patch("quack_core.core.fs.service.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = False

            with pytest.raises(QuackConfigurationError):
                provider.load_config(str(temp_dir / "nonexistent.yaml"))

        # Test invalid YAML
        with patch("quack_core.core.fs.service.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True

            with patch("quack_core.core.fs.service.standalone.read_yaml") as mock_read:
                mock_read.return_value.success = False
                mock_read.return_value.error = "Invalid YAML"

                with pytest.raises(QuackConfigurationError):
                    provider.load_config(str(config_file))

        # Test invalid configuration
        with patch("quack_core.core.fs.service.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True

            with patch("quack_core.core.fs.service.standalone.read_yaml") as mock_read:
                mock_read.return_value.success = True
                mock_read.return_value.data = {"wrong_section": {}}

                with patch.object(provider, "validate_config") as mock_validate:
                    mock_validate.return_value = False

                    result = provider.load_config(str(config_file))
                    assert result.success is False
                    assert result.error is not None
                    assert "validation failed" in result.error.lower()

    def test_load_config_raises_when_yaml_data_is_none(self, temp_dir: Path) -> None:
        """A successful read_yaml() that yields no data (e.g. an empty YAML
        file) must raise QuackConfigurationError rather than pass None into
        _extract_config, which would otherwise crash on `.get()`.
        """
        config_file = temp_dir / "empty_config.yaml"
        config_file.write_text("")

        provider = MockConfigProvider()

        with patch("quack_core.core.fs.service.standalone.get_file_info") as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True

            with patch("quack_core.core.fs.service.standalone.read_yaml") as mock_read:
                mock_read.return_value.success = True
                mock_read.return_value.data = None

                with pytest.raises(QuackConfigurationError, match="no data"):
                    provider.load_config(str(config_file))

    def test_extract_config_raises_when_section_is_not_a_mapping(self) -> None:
        """BaseConfigProvider._extract_config's own default implementation
        must reject a malformed config file where the integration's own
        section is not itself a mapping (e.g. a YAML list or scalar under
        the integration's key), rather than silently return the wrong type.

        MockConfigProvider overrides _extract_config, so the base class's
        own implementation is exercised directly via an unbound call,
        matching this repo's own established idiom for reaching a
        default method a fixture subclass otherwise shadows.
        """
        provider = MockConfigProvider()
        with pytest.raises(QuackConfigurationError, match="must be a mapping"):
            BaseConfigProvider._extract_config(
                provider, {"test_config": ["not", "a", "mapping"]}
            )

    def test_extract_config_returns_section_when_it_is_a_mapping(self) -> None:
        """BaseConfigProvider._extract_config's own default implementation
        returns the integration's section unchanged when it is a proper
        mapping -- the success path alongside the not-a-mapping guard above.
        """
        provider = MockConfigProvider()
        result = BaseConfigProvider._extract_config(
            provider, {"test_config": {"test_key": "test_value"}}
        )
        assert result == {"test_key": "test_value"}
