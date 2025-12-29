# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/base/test_auth_provider.py
# role: tests
# neighbors: __init__.py, auth_provider_impl.py, config_provider_impl.py, integration_service_impl.py, test_base.py, test_config_provider.py (+3 more)
# exports: TestBaseAuthProvider
# git_branch: refactor/toolkitWorkflow
# git_commit: 21a4e25
# === QV-LLM:END ===

"""
Tests for the BaseAuthProvider class.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from quack_core.integrations.core.base import BaseAuthProvider

from .auth_provider_impl import (
    MockAuthProvider,
)


class TestBaseAuthProvider:
    """Tests for the BaseAuthProvider class."""

    def test_init(self, temp_dir: Path) -> None:
        """Test initializing the auth provider."""
        # Test with credentials file
        credentials_file = str(temp_dir / "credentials.json")

        # Patch fs.service.standalone.resolve_path to return the expected path string
        with patch("quack_core.lib.fs.service.standalone.resolve_path") as mock_resolve:
            mock_resolve.return_value = credentials_file
            provider = MockAuthProvider(credentials_file=credentials_file)
            assert provider.credentials_file == credentials_file
            assert provider.authenticated is False
            assert provider.name == "test_auth"

        # Test without credentials file
        provider = MockAuthProvider()
        assert provider.credentials_file is None

    def test_resolve_path(self) -> None:
        """Test resolving a relative path."""
        provider = MockAuthProvider()

        # Test with absolute path
        abs_path = "/absolute/path"

        # Need to patch the proper method now
        with patch("quack_core.lib.fs.service.standalone.resolve_path") as mock_resolve:
            mock_resolve.return_value = abs_path
            resolved = provider._resolve_path(abs_path)
            assert resolved == abs_path
            mock_resolve.assert_called_once_with(abs_path)

        # Test with resolver exception - patch the fs service instance
        with patch("quack_core.lib.fs.service.standalone.resolve_path") as mock_resolve:
            mock_resolve.side_effect = Exception("Test error")

            with patch(
                    "quack_core.lib.fs.service.standalone.normalize_path") as mock_normalize:
                mock_normalize.return_value = "/normalized/path"

                resolved = provider._resolve_path("relative/path")
                assert resolved == "/normalized/path"
                mock_normalize.assert_called_once_with("relative/path")

    def test_abstract_methods(self) -> None:
        """Test that abstract methods must be implemented."""
        # Attempt to create a class without implementing the abstract methods
        with pytest.raises(TypeError):
            class InvalidProvider(BaseAuthProvider):
                pass

            InvalidProvider()  # This should raise TypeError

    def test_authenticate(self, temp_dir: Path) -> None:
        """Test authentication flow."""
        # Create a provider with credentials file
        credentials_file = temp_dir / "credentials.json"
        credentials_file.touch()

        # Use patch to verify that os.path.exists returns True for the credentials file
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True

            # Patch resolve_path to return a string
            with patch("quack_core.lib.fs.service.standalone.resolve_path") as mock_resolve:
                mock_resolve.return_value = str(credentials_file)
                provider = MockAuthProvider(credentials_file=str(credentials_file))

                # Test successful authentication
                result = provider.authenticate()
                assert result.success is True
                assert provider.authenticated is True

        # Test with missing credentials file
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            # Patch resolve_path to return a string
            with patch("quack_core.lib.fs.service.standalone.resolve_path") as mock_resolve:
                mock_resolve.return_value = "/nonexistent/path"
                provider = MockAuthProvider(credentials_file="/nonexistent/path")
                result = provider.authenticate()
                assert result.success is False
                assert "not found" in result.error

    def test_refresh_credentials(self) -> None:
        """Test refreshing credentials."""
        provider = MockAuthProvider()

        # Test refresh before authentication
        result = provider.refresh_credentials()
        assert result.success is False
        assert "Not authenticated" in result.error

        # Test refresh after authentication
        provider.authenticated = True
        result = provider.refresh_credentials()
        assert result.success is True
        assert "refreshed" in result.message

    def test_ensure_credentials_directory(self, temp_dir: Path) -> None:
        """Test ensuring the credentials directory exists."""
        # Test with existing directory
        credentials_file = str(temp_dir / "creds" / "credentials.json")

        # Patch resolve_path to return a string
        with patch("quack_core.lib.fs.service.standalone.resolve_path") as mock_resolve:
            mock_resolve.return_value = credentials_file
            provider = MockAuthProvider(credentials_file=credentials_file)

            # Now correctly patch the methods
            with patch("quack_core.lib.fs.service.standalone.split_path") as mock_split:
                mock_split.return_value = [str(temp_dir), "creds", "credentials.json"]

                with patch("quack_core.lib.fs.service.standalone.join_path") as mock_join:
                    mock_join.return_value = str(temp_dir / "creds")

                    with patch(
                            "quack_core.lib.fs.service.standalone.create_directory") as mock_create:
                        mock_result = MagicMock()
                        mock_result.success = True
                        mock_create.return_value = mock_result

                        result = provider._ensure_credentials_directory()
                        assert result is True
                        mock_create.assert_called_once()

        # Test with creation error
        with patch("quack_core.lib.fs.service.standalone.resolve_path") as mock_resolve:
            mock_resolve.return_value = credentials_file
            provider = MockAuthProvider(credentials_file=credentials_file)

            with patch("quack_core.lib.fs.service.standalone.split_path") as mock_split:
                mock_split.return_value = [str(temp_dir), "creds", "credentials.json"]

                with patch("quack_core.lib.fs.service.standalone.join_path") as mock_join:
                    mock_join.return_value = str(temp_dir / "creds")

                    with patch(
                            "quack_core.lib.fs.service.standalone.create_directory") as mock_create:
                        mock_result = MagicMock()
                        mock_result.success = False
                        mock_create.return_value = mock_result

                        result = provider._ensure_credentials_directory()
                        assert result is False

        # Test without credentials file
        provider = MockAuthProvider()
        result = provider._ensure_credentials_directory()
        assert result is False

    def test_base_save_credentials(self) -> None:
        """Test the default save_credentials implementation."""
        # Instead of trying to instantiate BaseAuthProvider directly,
        # create a concrete mock instance and replace its save_credentials method
        provider = MockAuthProvider()
        provider.logger = MagicMock()

        # Replace the save_credentials method with the one from BaseAuthProvider
        original_save = provider.save_credentials
        provider.save_credentials = BaseAuthProvider.save_credentials.__get__(
            provider, MockAuthProvider
        )

        try:
            result = provider.save_credentials()
            assert result is False
            provider.logger.warning.assert_called_once()
        finally:
            # Restore the original method
            provider.save_credentials = original_save
