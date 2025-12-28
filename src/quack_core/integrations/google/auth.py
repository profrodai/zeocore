# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/auth.py
# module: quack_core.integrations.google.auth
# role: module
# neighbors: __init__.py, config.py, serialization.py
# exports: GoogleAuthProvider
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
Google authentication provider for quack_core.

This module handles authentication with Google services, managing
credentials and authorization flows for secure API access.
"""

import logging
from collections.abc import Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from quack_core.lib.errors import QuackIntegrationError
from quack_core.lib.fs.service import standalone
from quack_core.integrations.core.base import BaseAuthProvider
from quack_core.integrations.core.results import AuthResult
from quack_core.integrations.google.serialization import serialize_credentials


class GoogleAuthProvider(BaseAuthProvider):
    """Authentication provider for Google integrations."""

    def __init__(
        self,
        client_secrets_file: str,
        credentials_file: str | None = None,
        scopes: list[str] | Sequence[str] | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        super().__init__(credentials_file, log_level)

        self.client_secrets_file = self._resolve_path(client_secrets_file)
        self.scopes = list(scopes) if scopes else []

        self._verify_client_secrets_file()

        self.auth: Credentials | None = None
        self.authenticated = False

    @property
    def name(self) -> str:
        return "GoogleAuth"

    def _verify_client_secrets_file(self) -> None:
        file_info = standalone.get_file_info(self.client_secrets_file)
        if not file_info.success or not file_info.exists:
            raise QuackIntegrationError(
                f"Client secrets file not found: {self.client_secrets_file}",
                {"path": str(self.client_secrets_file)},
            )

    def authenticate(self) -> AuthResult:
        try:
            creds = self._load_existing_credentials()

            if (
                creds
                and getattr(creds, "expired", False)
                and getattr(creds, "refresh_token", None)
            ):
                creds.refresh(Request())
                self._save_credentials_to_file(creds)
                self.auth = creds
                self.authenticated = True
                return self._build_auth_result(
                    creds, "Successfully refreshed credentials"
                )

            if not creds or not getattr(creds, "valid", False):
                self.logger.info(
                    "No valid credentials found, starting authentication flow"
                )

                # Extract the exact redirect URI from the client secrets file
                redirect_uri = self._extract_redirect_uri_from_secrets()

                if redirect_uri:
                    # Create flow with the client secrets file
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, self.scopes
                    )

                    # Parse the redirect URI to get the port and exact URI format
                    import urllib.parse

                    parsed_uri = urllib.parse.urlparse(redirect_uri)
                    port = (
                        parsed_uri.port or 8080
                    )  # Default to 8080 if no port specified

                    # Start the local server on the same port
                    # Set redirect_uri_trailing_slash=False to match the exact format in Google Cloud Console
                    creds = flow.run_local_server(
                        port=port, redirect_uri_trailing_slash=False
                    )
                else:
                    # Fallback to default behavior if redirect URI can't be extracted
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, self.scopes
                    )
                    creds = flow.run_local_server(port=0)

                self._save_credentials_to_file(creds)

            self.auth = creds
            self.authenticated = True
            return self._build_auth_result(
                creds, "Successfully authenticated with Google"
            )

        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            self.authenticated = False
            return AuthResult(
                success=False,
                message=None,
                error=f"Failed to authenticate with Google: {str(e)}",
            )

    def _extract_redirect_uri_from_secrets(self) -> str | None:
        """
        Extract the redirect URI from the client secrets file.

        Returns:
            str | None: The redirect URI or None if it couldn't be extracted
        """
        try:
            json_result = standalone.read_json(self.client_secrets_file)
            if not json_result.success:
                self.logger.warning(
                    f"Failed to read client secrets: {json_result.error}"
                )
                return None

            # Access the result data correctly
            data = json_result.data

            # Try web client configuration first (most common for installed apps)
            if "web" in data and "redirect_uris" in data["web"]:
                redirect_uris = data["web"]["redirect_uris"]
                if redirect_uris and len(redirect_uris) > 0:
                    return redirect_uris[0]

            # Try installed client configuration
            if (
                    "installed" in data
                    and "redirect_uris" in data["installed"]
            ):
                redirect_uris = data["installed"]["redirect_uris"]
                if redirect_uris and len(redirect_uris) > 0:
                    return redirect_uris[0]

            return None
        except Exception as e:
            self.logger.warning(
                f"Failed to extract redirect URI from client secrets: {e}"
            )
            return None

    def _load_existing_credentials(self) -> Credentials | None:
        file_info = standalone.get_file_info(self.credentials_file)
        if not file_info.exists:
            return None

        json_result = standalone.read_json(self.credentials_file)
        if not json_result.success:
            self.logger.warning(f"Failed to load credentials: {json_result.error}")
            return None

        try:
            # Access the result data correctly
            credential_data = json_result.data
            return Credentials.from_authorized_user_info(credential_data, self.scopes)
        except ValueError as e:
            self.logger.warning(f"Invalid credential data: {e}")
            return None

    def _build_auth_result(self, creds: Credentials, message: str) -> AuthResult:
        return AuthResult(
            success=True,
            message=message,
            token=str(getattr(creds, "token", None)),
            expiry=int(creds.expiry.timestamp())
            if getattr(creds, "expiry", None)
            else None,
            credentials_path=str(self.credentials_file),
        )

    def refresh_credentials(self) -> AuthResult:
        try:
            if not self.auth:
                return self.authenticate()

            if getattr(self.auth, "expired", False):
                self.auth.refresh(Request())
                self._save_credentials_to_file(self.auth)
                return self._build_auth_result(
                    self.auth, "Successfully refreshed credentials"
                )

            return self._build_auth_result(
                self.auth, "Credentials are valid, no refresh needed"
            )

        except Exception as e:
            self.logger.error(f"Failed to refresh credentials: {e}")
            self.authenticated = False
            return AuthResult(
                success=False,
                message=None,
                error=f"Failed to refresh Google credentials: {str(e)}",
            )

    def get_credentials(self) -> Credentials:
        if self.auth is None or not self.authenticated:
            result = self.authenticate()
            if not result.success:
                raise QuackIntegrationError(
                    "No valid Google credentials available",
                    {
                        "service": "Google",
                        "credentials_path": self.credentials_file,
                    },
                )
        return self.auth

    def save_credentials(self) -> bool:
        if self.auth is None:
            return False
        return self._save_credentials_to_file(self.auth)

    def _save_credentials_to_file(self, credentials: Credentials) -> bool:
        if not self.credentials_file:
            self.logger.warning("No credentials file specified, cannot save")
            return False

        split_result = standalone.split_path(self.credentials_file)
        if not split_result.success:
            self.logger.error(f"Failed to split path: {split_result.error}")
            return False

        # Extract the components and remove the last one (filename)
        path_components = split_result.data[:-1]
        if path_components:
            # Join them back together to get the directory path
            join_result = standalone.join_path(*path_components)

            # Handle both cases: join_path returning string directly or a DataResult
            directory_path = join_result
            if hasattr(join_result, 'success'):
                if not join_result.success:
                    self.logger.error(
                        f"Failed to join directory path: {join_result.error}")
                    return False
                directory_path = join_result.data

            # Create the directory
            result = standalone.create_directory(directory_path, exist_ok=True)
            if not result.success:
                self.logger.error(
                    f"Failed to create credentials directory: {result.error}"
                )
                return False

        try:
            data = serialize_credentials(credentials)
            result = standalone.write_json(self.credentials_file, data)
            if not result.success:
                self.logger.error(f"Failed to write credentials: {result.error}")
                return False
            return True

        except Exception as e:
            self.logger.error(f"Failed to serialize or save credentials: {e}")
            return False
