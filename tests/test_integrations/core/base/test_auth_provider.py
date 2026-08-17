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
        with patch(
            "quack_core.core.fs.service.standalone.resolve_path"
        ) as mock_resolve:
            mock_resolve.return_value = credentials_file
            provider = MockAuthProvider(credentials_file=credentials_file)
            assert provider.credentials_file == credentials_file
            assert provider.authenticated is False
            assert provider.name == "test_auth"

        # Test without credentials file
        provider = MockAuthProvider()
        assert provider.credentials_file is None

    def test_resolve_path(self) -> None:
        """Test resolving a relative path.

        RULING-237 s2.1 (quackverse-coverage-90): BaseAuthProvider._resolve_path's
        except-branch fallback used to call standalone.normalize_path as a
        second attempt after standalone.resolve_path failed -- but the two
        are literal aliases of the same sandboxed method
        (service/path_operations.py: resolve_path() is defined as
        `return self.normalize_path(path)`), so the "fallback" was a
        guaranteed second identical failure for the same input, not a
        genuine alternative. Fixed to mirror BaseConfigProvider's own
        sibling _resolve_path in the same file: on failure, log and return
        the raw, unresolved path string. This test now exercises the REAL
        standalone.resolve_path (no mock of the function under test, per
        RULING-235's own boundary-mock discipline) and asserts the real
        post-fix behavior for both the success and failure cases, rather
        than mocking standalone.normalize_path to prove a fallback shape
        that no longer exists."""
        provider = MockAuthProvider()

        # Real success case: a path inside the FileSystemService sandbox
        # resolves via the real standalone.resolve_path, no mock involved.
        resolved = provider._resolve_path("relative/path")
        assert resolved == str(Path.cwd() / "relative/path")

        # Real failure case: an absolute path outside the sandbox base_dir
        # makes the real standalone.resolve_path fail (QuackPathOutsideBaseDirError,
        # wrapped as a failed-Result ValueError at the coerce_path_str
        # boundary) -- the fixed fallback does NOT repeat the identical
        # sandboxed call; it logs a warning and returns the raw path
        # unresolved rather than crashing or silently returning None.
        outside_path = "/definitely/outside/the/sandbox/creds.json"
        resolved_outside = provider._resolve_path(outside_path)
        assert resolved_outside == outside_path

    def test_abstract_methods(self) -> None:
        """Test that abstract methods must be implemented."""
        # Attempt to create a class without implementing the abstract methods
        with pytest.raises(TypeError):

            class InvalidProvider(BaseAuthProvider):
                pass

            # Deliberately incomplete (implements none of the abstract methods)
            # -- this test's whole point is exercising Python's abstract-class
            # enforcement at instantiation time (see pytest.raises above).
            InvalidProvider()  # type: ignore[abstract]  # This should raise TypeError

    def test_authenticate(self, temp_dir: Path) -> None:
        """Test authentication flow."""
        # Create a provider with credentials file
        credentials_file = temp_dir / "credentials.json"
        credentials_file.touch()

        # Use patch to verify that os.path.exists returns True for the credentials file
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True

            # Patch resolve_path to return a string
            with patch(
                "quack_core.core.fs.service.standalone.resolve_path"
            ) as mock_resolve:
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
            with patch(
                "quack_core.core.fs.service.standalone.resolve_path"
            ) as mock_resolve:
                mock_resolve.return_value = "/nonexistent/path"
                provider = MockAuthProvider(credentials_file="/nonexistent/path")
                result = provider.authenticate()
                assert result.success is False
                assert result.error is not None
                assert "not found" in result.error

    def test_refresh_credentials(self) -> None:
        """Test refreshing credentials."""
        provider = MockAuthProvider()

        # Test refresh before authentication
        result = provider.refresh_credentials()
        assert result.success is False
        assert result.error is not None
        assert "Not authenticated" in result.error

        # Test refresh after authentication
        provider.authenticated = True
        result = provider.refresh_credentials()
        assert result.success is True
        assert result.message is not None
        assert "refreshed" in result.message

    def test_ensure_credentials_directory(self, temp_dir: Path) -> None:
        """Test ensuring the credentials directory exists."""
        # Test with existing directory
        credentials_file = str(temp_dir / "creds" / "credentials.json")

        # Patch resolve_path to return a string
        with patch(
            "quack_core.core.fs.service.standalone.resolve_path"
        ) as mock_resolve:
            mock_resolve.return_value = credentials_file
            provider = MockAuthProvider(credentials_file=credentials_file)

            # Now correctly patch the methods
            with patch(
                "quack_core.core.fs.service.standalone.split_path"
            ) as mock_split:
                mock_split.return_value = [str(temp_dir), "creds", "credentials.json"]

                with patch(
                    "quack_core.core.fs.service.standalone.join_path"
                ) as mock_join:
                    mock_join.return_value = str(temp_dir / "creds")

                    with patch(
                        "quack_core.core.fs.service.standalone.create_directory"
                    ) as mock_create:
                        mock_result = MagicMock()
                        mock_result.success = True
                        mock_create.return_value = mock_result

                        result = provider._ensure_credentials_directory()
                        assert result is True
                        mock_create.assert_called_once()

        # Test with creation error
        with patch(
            "quack_core.core.fs.service.standalone.resolve_path"
        ) as mock_resolve:
            mock_resolve.return_value = credentials_file
            provider = MockAuthProvider(credentials_file=credentials_file)

            with patch(
                "quack_core.core.fs.service.standalone.split_path"
            ) as mock_split:
                mock_split.return_value = [str(temp_dir), "creds", "credentials.json"]

                with patch(
                    "quack_core.core.fs.service.standalone.join_path"
                ) as mock_join:
                    mock_join.return_value = str(temp_dir / "creds")

                    with patch(
                        "quack_core.core.fs.service.standalone.create_directory"
                    ) as mock_create:
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
        # -- a deliberate runtime instance-level method swap (to exercise the
        # base class's default implementation through a concrete instance
        # without subclassing it directly); mypy correctly flags instance
        # method assignment as generally unsafe, but this is exactly what the
        # test needs.
        original_save = provider.save_credentials
        provider.save_credentials = BaseAuthProvider.save_credentials.__get__(  # type: ignore[method-assign]
            provider, MockAuthProvider
        )

        try:
            result = provider.save_credentials()
            assert result is False
            provider.logger.warning.assert_called_once()
        finally:
            # Restore the original method
            provider.save_credentials = original_save  # type: ignore[method-assign]
