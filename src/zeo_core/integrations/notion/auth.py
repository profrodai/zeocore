"""Authentication provider for Notion integration."""

import os
import time
from typing import Any, Protocol

from zeo_core.core.fs.service import standalone as fs
from zeo_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from zeo_core.integrations.core import AuthResult, BaseAuthProvider

from .transport import build_notion_http_client

logger = get_logger(__name__)


class _NotionSDKClient(Protocol):
    """Minimal protocol for the notion_client.Client used by the auth provider.

    Only the surface this provider calls (`users.me`) is named, so a test
    double needs to implement nothing else -- mirrors GitHubAuthProvider's
    own `_HTTPClient` Protocol shape one file over.
    """

    users: Any


class NotionAuthProvider(BaseAuthProvider):
    """Notion authentication provider using an internal integration token.

    Notion's own auth model is a single bearer "integration token" (created
    in the Notion integrations console, no OAuth dance for an internal
    integration) -- structurally identical to GitHub's personal access
    token, so this class mirrors GitHubAuthProvider's shape closely rather
    than Google's OAuth-flow-based GoogleAuthProvider.
    """

    def __init__(
        self,
        credentials_file: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        sdk_client_factory: Any = None,  # noqa: ANN401 -- injectable factory for testing; real default is notion_client.Client, imported lazily below (see initialize())
        trust_env: bool = False,
    ) -> None:
        """Initialize the Notion authentication provider.

        Args:
            credentials_file: Path to credentials file for storing the token
            log_level: Logging level
            sdk_client_factory: Optional factory ``(token) -> notion_client.Client``-
                shaped callable, for testing. Defaults to the real SDK client.
            trust_env: Whether the real SDK transport may inherit proxy settings.
        """
        super().__init__(credentials_file=credentials_file, log_level=log_level)
        self._token: str | None = None
        self._user_info: dict[str, Any] | None = None
        self._sdk_client_factory = sdk_client_factory
        self._trust_env = trust_env

        env_token = os.environ.get("NOTION_TOKEN")
        if env_token:
            self._token = env_token
            logger.debug("Loaded Notion token from environment variable")

    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        return "Notion"

    def _build_client(self, token: str) -> _NotionSDKClient:
        """Build (or fetch, via the injected factory) an SDK client for `token`."""
        if self._sdk_client_factory is not None:
            client: _NotionSDKClient = self._sdk_client_factory(token)
            return client

        from notion_client import Client as NotionSDKClient

        return NotionSDKClient(
            auth=token,
            client=build_notion_http_client(trust_env=self._trust_env),
        )

    def authenticate(self, token: str | None = None) -> AuthResult:
        """Authenticate with Notion using an integration token.

        Args:
            token: Notion integration token

        Returns:
            Authentication result
        """
        if token:
            self._token = token
            logger.debug("Using provided token for authentication")
        else:
            credentials = self._load_credentials()
            if credentials and credentials.get("token"):
                self._token = credentials.get("token")
                logger.debug("Loaded token from credentials file")

        if not self._token:
            env_token = os.environ.get("NOTION_TOKEN")
            if env_token:
                self._token = env_token
                logger.debug("Using token from environment variable")

        if not self._token:
            logger.error("No Notion token available for authentication")
            return AuthResult.error_result(
                error="No Notion token provided",
                message=(
                    "Please provide a valid Notion integration token via parameter, "
                    "credentials file, or the NOTION_TOKEN environment variable"
                ),
            )

        try:
            sdk_client = self._build_client(self._token)
            # Validate the token: notion_client raises APIResponseError with
            # code Unauthorized on a bad token (confirmed against
            # notion_client.errors.APIErrorCode.Unauthorized), so a
            # successful call is sufficient proof the token works.
            bot_user = sdk_client.users.me()

            self._user_info = bot_user if isinstance(bot_user, dict) else dict(bot_user)
            self._save_token_data(self._token)
            self.authenticated = True

            return AuthResult.success_result(
                message="Successfully authenticated with Notion",
                credentials_path=self.credentials_file,
                content={"user_info": self._user_info},
            )
        except Exception as e:
            status = getattr(e, "status", None)
            if status == 401:
                return AuthResult.error_result(
                    error="Invalid Notion token (unauthorized)",
                    message="Notion authentication failed",
                )
            return AuthResult.error_result(
                error="Notion API authentication failed",
                message="Notion authentication failed without exposing provider data",
            )

    def refresh_credentials(self) -> AuthResult:
        """Refresh Notion credentials.

        Note: Notion integration tokens don't expire/need refreshing, so
        this just re-validates the existing token (mirrors
        GitHubAuthProvider.refresh_credentials for the same reason: a
        personal-access-token-shaped credential has no refresh flow).

        Returns:
            Authentication result
        """
        if not self._token:
            return AuthResult.error_result(
                error="No Notion token available to refresh",
            )

        try:
            sdk_client = self._build_client(self._token)
            bot_user = sdk_client.users.me()
            self._user_info = bot_user if isinstance(bot_user, dict) else dict(bot_user)

            return AuthResult.success_result(
                message="Notion token is still valid",
                credentials_path=self.credentials_file,
            )
        except Exception:
            return AuthResult.error_result(
                error="Failed to validate Notion token",
            )

    def get_credentials(self) -> object:
        """Get the current Notion credentials.

        Returns:
            Dictionary with token and bot user information
        """
        if not self._token:
            credentials = self._load_credentials()
            if credentials and credentials.get("token"):
                self._token = credentials.get("token")

        return {"configured": self._token is not None, "user_info": self._user_info}

    def save_credentials(self) -> bool:
        """Save Notion credentials to file.

        Returns:
            True if credentials were saved, False otherwise
        """
        return self._save_token_data(self._token)

    def _load_credentials(self) -> dict[str, Any] | None:
        """Load Notion credentials from file."""
        if not self.credentials_file:
            logger.debug("No credentials file specified")
            return None

        file_info = fs.get_file_info(self.credentials_file)
        if not file_info.success or not file_info.exists:
            logger.debug(f"Credentials file does not exist: {self.credentials_file}")
            return None

        result = fs.read_json(self.credentials_file)
        if not result.success:
            logger.warning(f"Failed to read credentials file: {result.error}")
            return None

        logger.debug("Successfully loaded credentials from file")
        return result.data

    def _save_token_data(self, token: str | None) -> bool:
        """Save token data to credentials file."""
        if not token or not self.credentials_file:
            return False

        self._ensure_credentials_directory()

        credentials = {"token": token, "saved_at": int(time.time())}

        if self._user_info:
            credentials["user_info"] = self._user_info

        # 0600: this file holds a live bearer token (RULING-356 s4.4 item 4 /
        # config-secrets-hardening charter item 3).
        result = fs.write_json(
            self.credentials_file, credentials, atomic=True, mode=0o600
        )
        return result.success
