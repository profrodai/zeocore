"""
Tests for Google authentication provider.

This module tests the GoogleAuthProvider class, including authentication flow,
token management, and credential handling.
"""

from unittest.mock import MagicMock, patch

import pytest

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.integrations.core.results import AuthResult
from zeo_core.integrations.google.auth import GoogleAuthProvider

from .mocks import mock_credentials


class TestGoogleAuthProvider:
    """Tests for the GoogleAuthProvider class."""

    def test_init(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True

            provider = GoogleAuthProvider(client_secrets_file="/path/to/secrets.json")
            assert provider.name == "GoogleAuth"
            assert provider.scopes == []

    def test_verify_client_secrets_file(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            GoogleAuthProvider(client_secrets_file="/path/to/secrets.json")

        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = False
            with pytest.raises(ZeoIntegrationError):
                GoogleAuthProvider(client_secrets_file="/nonexistent/secrets.json")

    def test_authenticate_new_flow(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        with (
            patch("google.oauth2.credentials.Credentials") as mock_creds_class,
            patch(
                "zeo_core.integrations.google.auth.standalone.read_json"
            ) as mock_read,
            patch(
                "zeo_core.integrations.google.auth.InstalledAppFlow"
            ) as mock_flow_class,
        ):
            mock_read.return_value.success = True
            mock_read.return_value.data = {}

            expired_creds = mock_credentials(valid=False)
            mock_creds_class.from_authorized_user_info.return_value = expired_creds

            flow_instance = MagicMock()
            new_creds = mock_credentials(token="new_token", expiry_timestamp=1234567890)  # noqa: S106 -- test fixture, fake credential value, not a real secret
            flow_instance.run_local_server.return_value = new_creds
            mock_flow_class.from_client_secrets_file.return_value = flow_instance

            with patch.object(provider, "_save_credentials_to_file") as mock_save:
                mock_save.return_value = True
                result = provider.authenticate()

                assert result.success
                assert provider.authenticated
                assert provider.auth is new_creds
                assert provider.auth.token == "new_token"  # noqa: S105 -- provider-owned fake credential

    def test_authenticate_with_expired_credentials(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        refreshed_creds = mock_credentials(
            token="refreshed_token",  # noqa: S106 -- test fixture, fake credential value, not a real secret
            expired=True,
            refresh_token="refresh_token",  # noqa: S106 -- test fixture, fake credential value, not a real secret
            expiry_timestamp=1234567890,
        )

        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.read_json"
            ) as mock_read,
            patch("google.oauth2.credentials.Credentials") as mock_creds_class,
            patch("zeo_core.integrations.google.auth.Request"),
            patch.object(provider, "_save_credentials_to_file") as mock_save,
            patch(
                "zeo_core.integrations.google.auth.InstalledAppFlow"
            ) as mock_flow_class,
        ):
            mock_read.return_value.success = True
            mock_read.return_value.data = {}

            mock_creds_class.from_authorized_user_info.return_value = refreshed_creds

            mock_flow = MagicMock()
            mock_flow.run_local_server.return_value = refreshed_creds
            mock_flow_class.from_client_secrets_file.return_value = mock_flow

            mock_save.return_value = True

            result = provider.authenticate()

            assert result.success
            assert provider.auth is refreshed_creds
            assert provider.auth.token == "refreshed_token"  # noqa: S105 -- provider-owned fake credential

    def test_refresh_credentials(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        result = provider.refresh_credentials()
        assert not result.success

        provider.auth = mock_credentials(
            token="valid_token",  # noqa: S106 -- test fixture, fake credential value, not a real secret
            expired=False,
            expiry_timestamp=1234567890,
        )
        provider.authenticated = True

        result = provider.refresh_credentials()
        assert result.success
        assert result.message == "Credentials are valid, no refresh needed"
        assert provider.auth.token == "valid_token"  # noqa: S105 -- provider-owned fake credential

        provider.auth = mock_credentials(
            token="refreshed",  # noqa: S106 -- test fixture, fake credential value, not a real secret
            expired=True,
            refresh_token="yes",  # noqa: S106 -- test fixture, fake credential value, not a real secret
            expiry_timestamp=1234567890,
        )

        with patch.object(provider, "_save_credentials_to_file") as mock_save:
            mock_save.return_value = True
            result = provider.refresh_credentials()
            assert result.success
            assert result.message == "Successfully refreshed credentials"
            assert provider.auth.token == "refreshed"  # noqa: S105 -- provider-owned fake credential

        broken_creds = mock_credentials(expired=True, refresh_token="yes")  # noqa: S106 -- test fixture, fake credential value, not a real secret
        broken_creds.refresh.side_effect = Exception("refresh error")
        provider.auth = broken_creds

        result = provider.refresh_credentials()
        assert not result.success
        assert result.error is not None
        assert "Failed to refresh" in result.error

    def test_get_credentials(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        with patch.object(provider, "authenticate") as mock_auth:
            mock_auth.return_value = AuthResult(success=False, error="fail")
            with pytest.raises(ZeoIntegrationError):
                provider.get_credentials()

        valid_creds = mock_credentials(token="X")  # noqa: S106 -- test fixture, fake credential value, not a real secret
        provider.auth = valid_creds
        provider.authenticated = True
        assert provider.get_credentials() == valid_creds

        provider.auth = None
        provider.authenticated = False

        with patch.object(provider, "authenticate") as mock_auth:
            new_creds = mock_credentials(token="new")  # noqa: S106 -- test fixture, fake credential value, not a real secret
            provider.auth = new_creds
            provider.authenticated = True
            mock_auth.return_value = AuthResult(success=True)
            assert provider.get_credentials() == new_creds

    def test_save_credentials(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        provider.auth = None
        assert not provider.save_credentials()

        provider.auth = mock_credentials(token="x")  # noqa: S106 -- test fixture, fake credential value, not a real secret
        with patch.object(provider, "_save_credentials_to_file") as mock_save:
            mock_save.return_value = True
            assert provider.save_credentials()

    def test_save_credentials_to_file(self) -> None:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

        provider.credentials_file = None
        assert not provider._save_credentials_to_file(mock_credentials())

        provider.credentials_file = "/path/to/credentials.json"
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.split_path"
            ) as mock_split,
            patch(
                "zeo_core.integrations.google.auth.standalone.join_path"
            ) as mock_join,
            patch(
                "zeo_core.integrations.google.auth.standalone.create_directory"
            ) as mock_mkdir,
        ):
            split_result = MagicMock()
            split_result.success = True
            split_result.data = ["path", "to", "credentials.json"]
            mock_split.return_value = split_result

            join_result = MagicMock()
            join_result.success = True
            join_result.data = "/path/to"
            mock_join.return_value = join_result

            mock_mkdir.return_value.success = False
            assert not provider._save_credentials_to_file(mock_credentials())

        creds = mock_credentials(token="test_token", expiry_timestamp=1234567890)  # noqa: S106 -- test fixture, fake credential value, not a real secret
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.split_path"
            ) as mock_split,
            patch(
                "zeo_core.integrations.google.auth.standalone.join_path"
            ) as mock_join,
            patch(
                "zeo_core.integrations.google.auth.standalone.create_directory"
            ) as mock_mkdir,
            patch(
                "zeo_core.integrations.google.auth.standalone.write_json"
            ) as mock_write_json,
        ):
            split_result = MagicMock()
            split_result.success = True
            split_result.data = ["path", "to", "credentials.json"]
            mock_split.return_value = split_result

            join_result = MagicMock()
            join_result.success = True
            join_result.data = "/path/to"
            mock_join.return_value = join_result

            mock_mkdir.return_value.success = True
            mock_write_json.return_value.success = True

            assert provider._save_credentials_to_file(creds)
            mock_write_json.assert_called_once()
            # config-secrets-hardening charter item 3 / RULING-356 s4.4 item
            # 4: google/auth.py:288 must pass mode=0600 through to the fs
            # write path so a live OAuth credential never lands world- or
            # group-readable.
            _, call_kwargs = mock_write_json.call_args
            assert call_kwargs.get("mode") == 0o600


class TestGoogleAuthProviderCoverageGaps:
    """Additional tests for GoogleAuthProvider covering branches not
    exercised by TestGoogleAuthProvider above: the authenticate() refresh
    path taken when _load_existing_credentials returns expired creds with a
    refresh_token, the new-auth-flow path when a redirect URI IS extracted
    from the client secrets file, _extract_redirect_uri_from_secrets's
    web/installed/exception branches, _load_existing_credentials's full
    body, and the remaining _save_credentials_to_file error branches.

    Per RULING-235, only the external SDK/network boundary is mocked here:
    google.oauth2.credentials.Credentials, google_auth_oauthlib's
    InstalledAppFlow, google.auth.transport.requests.Request, and the
    core/fs `standalone` module (the documented fs-sandbox-wall escape
    hatch) -- never GoogleAuthProvider's own methods under test, except
    where a helper method itself is the seam between two branches we want
    to isolate (e.g. patching _load_existing_credentials to directly
    supply the precondition for the refresh branch in authenticate()).
    """

    def _make_provider(self) -> GoogleAuthProvider:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            return GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )

    def test_authenticate_refresh_path(self) -> None:
        """Covers auth.py:66-70 -- when _load_existing_credentials returns
        creds that are both expired and carry a refresh_token, authenticate()
        refreshes them in place (via Request()) rather than starting a new
        OAuth flow, saves them, and returns a success AuthResult."""
        provider = self._make_provider()

        expired_creds = mock_credentials(
            token="pre_refresh",  # noqa: S106 -- test fixture, fake credential value, not a real secret
            expired=True,
            refresh_token="has_one",  # noqa: S106 -- test fixture, fake credential value, not a real secret
            expiry_timestamp=1234567890,
        )

        def fake_refresh(request: object) -> None:
            expired_creds.token = "post_refresh"  # noqa: S105 -- test fixture, fake credential value, not a real secret

        expired_creds.refresh.side_effect = fake_refresh

        with (
            patch.object(
                provider, "_load_existing_credentials", return_value=expired_creds
            ),
            patch("zeo_core.integrations.google.auth.Request") as mock_request_cls,
            patch.object(provider, "_save_credentials_to_file") as mock_save,
        ):
            mock_save.return_value = True

            result = provider.authenticate()

            assert result.success
            assert result.message == "Successfully refreshed credentials"
            assert provider.auth is expired_creds
            assert provider.auth.token == "post_refresh"  # noqa: S105 -- provider-owned fake credential
            assert provider.authenticated is True
            expired_creds.refresh.assert_called_once()
            mock_request_cls.assert_called_once()
            mock_save.assert_called_once_with(expired_creds)

    def test_authenticate_new_flow_with_redirect_uri(self) -> None:
        """Covers auth.py:84-99 -- when a redirect URI IS successfully
        extracted from the client secrets file, authenticate() builds the
        flow, parses the port out of the redirect URI (falling back to 8080
        when unset), and calls run_local_server with that exact port and
        redirect_uri_trailing_slash=False -- the non-fallback branch, distinct
        from test_authenticate_new_flow in TestGoogleAuthProvider (which never
        supplies a redirect_uri, so it exercises the "else" fallback at
        auth.py:103-107 rather than this branch)."""
        provider = self._make_provider()

        new_creds = mock_credentials(
            token="from_flow",  # noqa: S106 -- test fixture, fake credential value, not a real secret
            expiry_timestamp=1234567890,
        )

        with (
            patch.object(provider, "_load_existing_credentials", return_value=None),
            patch.object(
                provider,
                "_extract_redirect_uri_from_secrets",
                return_value="http://localhost:9999/",
            ),
            patch(
                "zeo_core.integrations.google.auth.InstalledAppFlow"
            ) as mock_flow_class,
            patch.object(provider, "_save_credentials_to_file") as mock_save,
        ):
            flow_instance = MagicMock()
            flow_instance.run_local_server.return_value = new_creds
            mock_flow_class.from_client_secrets_file.return_value = flow_instance
            mock_save.return_value = True

            result = provider.authenticate()

            assert result.success
            assert provider.auth is new_creds
            assert provider.auth.token == "from_flow"  # noqa: S105 -- provider-owned fake credential
            mock_flow_class.from_client_secrets_file.assert_called_once_with(
                provider.client_secrets_file, provider.scopes
            )
            flow_instance.run_local_server.assert_called_once_with(
                port=9999, redirect_uri_trailing_slash=False
            )
            mock_save.assert_called_once_with(new_creds)

    def test_authenticate_new_flow_redirect_uri_no_port_defaults_8080(self) -> None:
        """Covers the `parsed_uri.port or 8080` fallback on auth.py:92-94
        when the extracted redirect URI has no explicit port."""
        provider = self._make_provider()
        new_creds = mock_credentials(token="no_port")  # noqa: S106 -- test fixture, fake credential value, not a real secret

        with (
            patch.object(provider, "_load_existing_credentials", return_value=None),
            patch.object(
                provider,
                "_extract_redirect_uri_from_secrets",
                return_value="http://localhost/",
            ),
            patch(
                "zeo_core.integrations.google.auth.InstalledAppFlow"
            ) as mock_flow_class,
            patch.object(provider, "_save_credentials_to_file", return_value=True),
        ):
            flow_instance = MagicMock()
            flow_instance.run_local_server.return_value = new_creds
            mock_flow_class.from_client_secrets_file.return_value = flow_instance

            result = provider.authenticate()

            assert result.success
            flow_instance.run_local_server.assert_called_once_with(
                port=8080, redirect_uri_trailing_slash=False
            )

    def test_authenticate_generic_exception_returns_error_result(self) -> None:
        """Covers the broad `except Exception` at the bottom of
        authenticate() (already partially covered, but pinned explicitly
        here) via a boundary failure in _load_existing_credentials."""
        provider = self._make_provider()

        with patch.object(
            provider,
            "_load_existing_credentials",
            side_effect=RuntimeError("boundary blew up"),
        ):
            result = provider.authenticate()
            assert not result.success
            assert result.error is not None
            assert "Failed to authenticate with Google" in result.error
            assert provider.authenticated is False

    def test_extract_redirect_uri_web_config(self) -> None:
        """Covers auth.py:146-148 -- the 'web' client-config branch."""
        provider = self._make_provider()
        with patch(
            "zeo_core.integrations.google.auth.standalone.read_json"
        ) as mock_read:
            mock_read.return_value = MagicMock(
                success=True,
                data={"web": {"redirect_uris": ["http://localhost:1234/cb"]}},
            )
            uri = provider._extract_redirect_uri_from_secrets()
            assert uri == "http://localhost:1234/cb"

    def test_extract_redirect_uri_installed_config(self) -> None:
        """Covers auth.py:152-154 -- the 'installed' client-config branch,
        reached only when no 'web' key with redirect_uris is present."""
        provider = self._make_provider()
        with patch(
            "zeo_core.integrations.google.auth.standalone.read_json"
        ) as mock_read:
            mock_read.return_value = MagicMock(
                success=True,
                data={"installed": {"redirect_uris": ["http://localhost:5678/cb"]}},
            )
            uri = provider._extract_redirect_uri_from_secrets()
            assert uri == "http://localhost:5678/cb"

    def test_extract_redirect_uri_no_matching_config_returns_none(self) -> None:
        """Covers auth.py:156 -- neither 'web' nor 'installed' present."""
        provider = self._make_provider()
        with patch(
            "zeo_core.integrations.google.auth.standalone.read_json"
        ) as mock_read:
            mock_read.return_value = MagicMock(success=True, data={})
            assert provider._extract_redirect_uri_from_secrets() is None

    def test_extract_redirect_uri_read_failure_returns_none(self) -> None:
        """Covers auth.py:135-139 -- read_json() failing returns None
        (already-covered defensive branch, pinned alongside the new ones
        for completeness of this method's coverage)."""
        provider = self._make_provider()
        with patch(
            "zeo_core.integrations.google.auth.standalone.read_json"
        ) as mock_read:
            mock_read.return_value = MagicMock(success=False, error="boom", data=None)
            assert provider._extract_redirect_uri_from_secrets() is None

    def test_extract_redirect_uri_exception_returns_none(self) -> None:
        """Covers auth.py:157-161 -- an unexpected exception (e.g. malformed
        data shape raising on subscript/containment checks) is caught,
        logged, and swallowed to None rather than propagating.

        Uses data=42 (not None) so this exercises the try/except's own
        catch-all, distinct from test_extract_redirect_uri_data_none_returns_none
        below which covers the explicit `data is None` guard added in the
        lint-mypy-backlog round18 google/auth.py cluster fix -- that guard
        now intercepts the None case before it ever reaches `"web" in data`.
        """
        provider = self._make_provider()
        with patch(
            "zeo_core.integrations.google.auth.standalone.read_json"
        ) as mock_read:
            mock_read.return_value = MagicMock(success=True, data=42)
            # `"web" in data` raises TypeError when data is a non-iterable int.
            uri = provider._extract_redirect_uri_from_secrets()
            assert uri is None

    def test_extract_redirect_uri_data_none_returns_none(self) -> None:
        """Covers auth.py's `_extract_redirect_uri_from_secrets` data-is-None
        guard, added in the lint-mypy-backlog round18 google/auth.py cluster
        fix: read_json() can report success=True while data is None
        (DataResult.data is itself Optional at the model level), which must
        short-circuit to None rather than reach `"web" in data`."""
        provider = self._make_provider()
        with patch(
            "zeo_core.integrations.google.auth.standalone.read_json"
        ) as mock_read:
            mock_read.return_value = MagicMock(success=True, data=None)
            uri = provider._extract_redirect_uri_from_secrets()
            assert uri is None

    def test_load_existing_credentials_file_missing(self) -> None:
        """Covers auth.py:164-166 -- get_file_info().exists is False."""
        provider = self._make_provider()
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value = MagicMock(exists=False)
            assert provider._load_existing_credentials() is None

    def test_load_existing_credentials_read_json_failure(self) -> None:
        """Covers auth.py:168-171 -- get_file_info().exists True but
        read_json() fails."""
        provider = self._make_provider()
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.get_file_info"
            ) as mock_info,
            patch(
                "zeo_core.integrations.google.auth.standalone.read_json"
            ) as mock_read,
        ):
            mock_info.return_value = MagicMock(exists=True)
            mock_read.return_value = MagicMock(success=False, error="disk error")
            assert provider._load_existing_credentials() is None

    def test_load_existing_credentials_success(self) -> None:
        """Covers auth.py:173-176 -- the happy path: file exists, JSON reads
        successfully, and Credentials.from_authorized_user_info builds the
        credentials object from the parsed data."""
        provider = self._make_provider()
        built_creds = mock_credentials(token="loaded")  # noqa: S106 -- fake test value
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.get_file_info"
            ) as mock_info,
            patch(
                "zeo_core.integrations.google.auth.standalone.read_json"
            ) as mock_read,
            patch("zeo_core.integrations.google.auth.Credentials") as mock_creds_class,
        ):
            mock_info.return_value = MagicMock(exists=True)
            mock_read.return_value = MagicMock(success=True, data={"token": "loaded"})
            mock_creds_class.from_authorized_user_info.return_value = built_creds

            result = provider._load_existing_credentials()

            assert result is built_creds
            mock_creds_class.from_authorized_user_info.assert_called_once_with(
                {"token": "loaded"}, provider.scopes
            )

    def test_load_existing_credentials_invalid_data_returns_none(self) -> None:
        """Covers auth.py:177-179 -- Credentials.from_authorized_user_info
        raising ValueError (malformed credential JSON) is caught and
        swallowed to None."""
        provider = self._make_provider()
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.get_file_info"
            ) as mock_info,
            patch(
                "zeo_core.integrations.google.auth.standalone.read_json"
            ) as mock_read,
            patch("zeo_core.integrations.google.auth.Credentials") as mock_creds_class,
        ):
            mock_info.return_value = MagicMock(exists=True)
            mock_read.return_value = MagicMock(success=True, data={"bad": "shape"})
            mock_creds_class.from_authorized_user_info.side_effect = ValueError(
                "invalid data"
            )

            assert provider._load_existing_credentials() is None

    def test_save_credentials_to_file_split_path_failure(self) -> None:
        """Covers auth.py:240-243 -- split_path() itself failing."""
        provider = self._make_provider()
        with patch(
            "zeo_core.integrations.google.auth.standalone.split_path"
        ) as mock_split:
            mock_split.return_value = MagicMock(success=False, error="split boom")
            assert not provider._save_credentials_to_file(mock_credentials())

    def test_save_credentials_to_file_join_result_failure(self) -> None:
        """Covers auth.py:252-258 -- join_path() returning a Result-like
        object (has a `.success` attribute) that reports failure."""
        provider = self._make_provider()
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.split_path"
            ) as mock_split,
            patch(
                "zeo_core.integrations.google.auth.standalone.join_path"
            ) as mock_join,
        ):
            mock_split.return_value = MagicMock(
                success=True, data=["path", "to", "credentials.json"]
            )
            mock_join.return_value = MagicMock(success=False, error="join boom")

            assert not provider._save_credentials_to_file(mock_credentials())

    def test_save_credentials_to_file_write_json_failure(self) -> None:
        """Covers auth.py:271-274 -- write_json() reporting failure after a
        successful directory setup."""
        provider = self._make_provider()
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.split_path"
            ) as mock_split,
            patch(
                "zeo_core.integrations.google.auth.standalone.join_path"
            ) as mock_join,
            patch(
                "zeo_core.integrations.google.auth.standalone.create_directory"
            ) as mock_mkdir,
            patch(
                "zeo_core.integrations.google.auth.standalone.write_json"
            ) as mock_write_json,
        ):
            mock_split.return_value = MagicMock(
                success=True, data=["path", "to", "credentials.json"]
            )
            mock_join.return_value = MagicMock(success=True, data="/path/to")
            mock_mkdir.return_value = MagicMock(success=True)
            mock_write_json.return_value = MagicMock(success=False, error="write boom")

            assert not provider._save_credentials_to_file(
                mock_credentials(token="x")  # noqa: S106 -- fake test value
            )

    def test_save_credentials_to_file_serialize_exception(self) -> None:
        """Covers auth.py:277-279 -- an exception raised while serializing
        or writing credentials (e.g. serialize_credentials blowing up on a
        malformed credentials object) is caught, logged, and returns False
        rather than propagating."""
        provider = self._make_provider()
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.split_path"
            ) as mock_split,
            patch(
                "zeo_core.integrations.google.auth.serialize_credentials"
            ) as mock_serialize,
        ):
            mock_split.return_value = MagicMock(success=True, data=["credentials.json"])
            mock_serialize.side_effect = RuntimeError("serialize boom")

            assert not provider._save_credentials_to_file(mock_credentials())

    def test_load_existing_credentials_no_credentials_file_returns_none(self) -> None:
        """Covers auth.py's `_load_existing_credentials` credentials_file
        None guard, added in the lint-mypy-backlog round18 google/auth.py
        cluster fix (Response | None-shaped narrowing, applied here to
        self.credentials_file: str | None). A provider constructed without
        a credentials_file must short-circuit to None rather than pass
        None into standalone.get_file_info/read_json."""
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            provider = GoogleAuthProvider(client_secrets_file="/path/to/secrets.json")

        assert provider.credentials_file is None
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            assert provider._load_existing_credentials() is None
            mock_info.assert_not_called()

    def test_load_existing_credentials_data_none_returns_none(self) -> None:
        """Covers auth.py's `_load_existing_credentials` credential_data
        None guard: read_json() can report success=True while data is None
        (DataResult.data is itself Optional at the model level) -- this
        must be treated the same as a read failure, not passed into
        Credentials.from_authorized_user_info untyped."""
        provider = self._make_provider()
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.get_file_info"
            ) as mock_info,
            patch(
                "zeo_core.integrations.google.auth.standalone.read_json"
            ) as mock_read,
        ):
            mock_info.return_value = MagicMock(exists=True)
            mock_read.return_value = MagicMock(success=True, data=None)
            assert provider._load_existing_credentials() is None

    def test_get_credentials_raises_when_auth_still_none_after_authenticate(
        self,
    ) -> None:
        """Covers get_credentials()'s defensive backstop: authenticate()
        reporting success=True is expected to have set self.auth as a side
        effect (both its refresh and fresh-flow branches do), but if that
        invariant is ever violated, get_credentials() must raise rather
        than return None from a function typed to return Credentials
        (the source of the [return-value] mypy finding this cluster
        fixed). Directly exercised by patching authenticate() to report
        success without setting self.auth, which real callers cannot do
        but the type system cannot rule out."""
        provider = self._make_provider()
        provider.auth = None
        provider.authenticated = False

        with patch.object(provider, "authenticate") as mock_auth:
            mock_auth.return_value = AuthResult(success=True)
            with pytest.raises(ZeoIntegrationError, match="no credentials were set"):
                provider.get_credentials()


class TestGoogleAuthProviderScopeSufficiency:
    """RULING-406 gate one / RULING-408: `_load_existing_credentials` must
    validate GRANTED scopes (recorded in the credential file at save time)
    against REQUESTED scopes (self.scopes), not trust
    `Credentials.from_authorized_user_info`'s own `.scopes`/`.expired`/
    `.valid` -- that SDK call stamps the REQUESTED scopes onto the returned
    object regardless of what was actually granted, so a token granted
    drive-only, loaded with spreadsheets requested, comes back with
    `creds.scopes == ['.../spreadsheets']`, `expired False`, `valid True`:
    it passes both of authenticate()'s only checks and then 403s at
    runtime. This is the exact defect the org ledger records as VERIFIED
    (auth-scope-defect-passes-the-only-gate, zeocore@f315f97f) by executing
    it, not reading it -- test_insufficient_scope_defect_reproduced_live
    below re-executes that same defect against the REAL google-auth SDK
    (not a MagicMock) as the ground truth this whole feature exists to
    catch, before testing the fix that catches it.
    """

    def _make_provider(self, scopes: list[str]) -> GoogleAuthProvider:
        with patch(
            "zeo_core.integrations.google.auth.standalone.get_file_info"
        ) as mock_info:
            mock_info.return_value.success = True
            mock_info.return_value.exists = True
            return GoogleAuthProvider(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
                scopes=scopes,
            )

    def test_insufficient_scope_defect_reproduced_live(self) -> None:
        """The bytes the org ledger's first row claims VERIFIED, re-executed
        here against the real SDK (no mocks) as a standing regression proof
        that the defect this feature exists to catch is real, not assumed:
        a drive-only-granted credential, loaded with spreadsheets
        requested, comes back scopes==REQUESTED (not granted),
        expired=False, valid=True."""
        from google.oauth2.credentials import Credentials

        granted_only_drive = {
            "token": "tok",  # noqa: S106 -- fake test value
            "refresh_token": "rtok",  # noqa: S106 -- fake test value
            "client_id": "cid",
            "client_secret": "csecret",  # noqa: S106 -- fake test value
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/drive"],
            "expiry": "2099-01-01T00:00:00Z",
        }
        requested_spreadsheets = ["https://www.googleapis.com/auth/spreadsheets"]

        creds = Credentials.from_authorized_user_info(
            granted_only_drive, requested_spreadsheets
        )

        # This IS the defect: the object claims the REQUESTED scope, not
        # the drive-only scope actually on disk, and reports itself usable.
        assert creds.scopes == requested_spreadsheets
        assert creds.expired is False
        assert creds.valid is True
        # ...which is exactly why authenticate()'s old expired/valid-only
        # gate could not have caught this -- both checks pass.

    def test_load_existing_credentials_returns_none_when_scope_insufficient(
        self,
    ) -> None:
        """The fix: _load_existing_credentials itself must catch what the
        expired/valid checks cannot, by comparing the file's recorded
        `scopes` (granted) against self.scopes (requested) BEFORE trusting
        the loaded credential -- forcing a return of None (which
        authenticate() already treats as "start a new flow, i.e. re-consent")
        when spreadsheets was requested but only drive was ever granted."""
        provider = self._make_provider(
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        # Deliberately NOT mocking google.oauth2.credentials.Credentials
        # here: this must be a complete, real-SDK-valid authorized_user_info
        # payload (matching test_insufficient_scope_defect_reproduced_live's
        # own shape) so that if the scope-sufficiency check under test were
        # ever deleted, the real Credentials.from_authorized_user_info call
        # would succeed and return a usable (mis-scoped) credential rather
        # than raising ValueError for an unrelated reason (missing fields)
        # that would make this test pass for the WRONG reason -- exactly
        # the class of test RULING-357 s6 warns cannot actually fail.
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.get_file_info"
            ) as mock_info,
            patch(
                "zeo_core.integrations.google.auth.standalone.read_json"
            ) as mock_read,
        ):
            mock_info.return_value = MagicMock(exists=True)
            mock_read.return_value = MagicMock(
                success=True,
                data={
                    "token": "tok",  # noqa: S106 -- fake test value
                    "refresh_token": "rtok",  # noqa: S106 -- fake test value
                    "client_id": "cid",
                    "client_secret": "csecret",  # noqa: S106 -- fake test value
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "scopes": ["https://www.googleapis.com/auth/drive"],
                    "expiry": "2099-01-01T00:00:00Z",
                },
            )

            result = provider._load_existing_credentials()

            assert result is None

    def test_load_existing_credentials_returns_creds_when_scope_sufficient(
        self,
    ) -> None:
        """The non-regression half: a credential granting a superset of
        what's requested (or exactly what's requested) still loads
        normally -- this feature must narrow the happy path, not remove
        it."""
        provider = self._make_provider(
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )

        built_creds = mock_credentials(token="loaded")  # noqa: S106 -- fake test value
        with (
            patch(
                "zeo_core.integrations.google.auth.standalone.get_file_info"
            ) as mock_info,
            patch(
                "zeo_core.integrations.google.auth.standalone.read_json"
            ) as mock_read,
            patch("zeo_core.integrations.google.auth.Credentials") as mock_creds_class,
        ):
            mock_info.return_value = MagicMock(exists=True)
            mock_read.return_value = MagicMock(
                success=True,
                data={
                    "token": "tok",  # noqa: S106 -- fake test value
                    "scopes": [
                        "https://www.googleapis.com/auth/drive",
                        "https://www.googleapis.com/auth/drive.file",
                    ],
                },
            )
            mock_creds_class.from_authorized_user_info.return_value = built_creds

            result = provider._load_existing_credentials()

            assert result is built_creds

    def test_has_sufficient_scopes_no_scopes_requested_is_always_sufficient(
        self,
    ) -> None:
        """A provider constructed with no explicit scopes never had a
        specific requirement to fall short of -- self.scopes == [] must
        short-circuit to sufficient rather than fail-closed on an empty
        request, matching every pre-existing test that constructs a
        provider without a scopes= kwarg."""
        provider = self._make_provider(scopes=[])
        assert provider._has_sufficient_scopes({"scopes": []}, MagicMock()) is True
        assert (
            provider._has_sufficient_scopes(
                {"scopes": ["https://www.googleapis.com/auth/drive"]}, MagicMock()
            )
            is True
        )

    def test_has_sufficient_scopes_missing_scopes_key_fails_closed(self) -> None:
        """credential_data with no recorded `scopes` list at all (malformed,
        or written by something other than serialize_credentials) has no
        grant to check against -- fail closed and force re-consent, rather
        than trust an un-attributed credential."""
        provider = self._make_provider(scopes=["https://www.googleapis.com/auth/drive"])
        assert provider._has_sufficient_scopes({}, MagicMock()) is False
        assert (
            provider._has_sufficient_scopes({"scopes": "not-a-list"}, MagicMock())
            is False
        )
