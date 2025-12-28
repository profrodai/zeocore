# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/auth.py
# module: quack_core.integrations.github.auth
# role: module
# neighbors: __init__.py, service.py, models.py, protocols.py, config.py, client.py
# exports: GitHubAuthProvider
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""Authentication provider for GitHub integration."""

import os
import time
from typing import Any

import requests

from quack_core.lib.fs import service as fs
from quack_core.integrations.core import AuthResult, BaseAuthProvider
from quack_core.lib.logging import get_logger

logger = get_logger(__name__)


class GitHubAuthProvider(BaseAuthProvider):
    """GitHub authentication provider using personal access tokens."""

    def __init__(
        self,
        credentials_file: str | None = None,
        log_level: int | str | None = None,
        http_client=None,  # Allows injection of a client for testing
    ) -> None:
        """Initialize the GitHub authentication provider.

        Args:
            credentials_file: Path to credentials file for storing the token
            log_level: Logging level
            http_client: Optional HTTP client for testing
        """
        # Default to INFO level if None is provided
        super().__init__(
            credentials_file=credentials_file, log_level=log_level or "INFO"
        )
        self.token = None
        self._user_info = None
        self._http_client = http_client or requests

        # Check token from environment variable immediately
        env_token = os.environ.get("GITHUB_TOKEN")
        if env_token:
            self.token = env_token
            logger.debug("Loaded GitHub token from environment variable")

    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        return "GitHub"

    def authenticate(self, token: str | None = None) -> AuthResult:
        """Authenticate with GitHub using a personal access token.

        Args:
            token: GitHub personal access token

        Returns:
            Authentication result
        """
        # First, try to use the provided token
        if token:
            self.token = token
            logger.debug("Using provided token for authentication")
        else:
            # If no token provided, try to load from credentials file
            credentials = self._load_credentials()
            if credentials and credentials.get("token"):
                self.token = credentials.get("token")
                logger.debug("Loaded token from credentials file")

        # If still no token, try environment variable (again, for safety)
        if not self.token:
            env_token = os.environ.get("GITHUB_TOKEN")
            if env_token:
                self.token = env_token
                logger.debug("Using token from environment variable")

        if not self.token:
            logger.error("No GitHub token available for authentication")
            return AuthResult.error_result(
                error="No GitHub token provided",
                message="Please provide a valid GitHub token via parameter, credentials file, or the GITHUB_TOKEN environment variable",
            )

        # Validate the token by making a test request to the GitHub API
        try:
            response = self._http_client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {self.token}"},
            )

            response.raise_for_status()

            # Store user info for later use
            self._user_info = response.json()

            # Token is valid, save it for future use
            self._save_token_data(self.token)

            self.authenticated = True

            return AuthResult.success_result(
                token=self.token,
                message="Successfully authenticated with GitHub",
                credentials_path=self.credentials_file,
                content={"user_info": self._user_info},
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_message = (
                f"GitHub API authentication failed with status {status_code}"
            )

            if status_code == 401:
                error_message = "Invalid GitHub token (unauthorized)"
            elif status_code == 403:
                error_message = "GitHub token lacks required permissions"

            return AuthResult.error_result(
                error=error_message,
                message=e.response.text if hasattr(e, "response") else str(e),
            )
        except requests.exceptions.RequestException as e:
            return AuthResult.error_result(
                error=f"GitHub API connection error: {str(e)}",
            )

    def refresh_credentials(self) -> AuthResult:
        """Refresh GitHub credentials.

        Note: GitHub Personal Access Tokens don't need refreshing, so this
        just validates the existing token.

        Returns:
            Authentication result
        """
        if not self.token:
            return AuthResult.error_result(
                error="No GitHub token available to refresh",
            )

        # For PATs, we just validate that the token still works
        try:
            response = self._http_client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {self.token}"},
            )

            response.raise_for_status()

            # Update user info
            self._user_info = response.json()

            return AuthResult.success_result(
                token=self.token,
                message="GitHub token is still valid",
                credentials_path=self.credentials_file,
            )
        except requests.exceptions.RequestException as e:
            return AuthResult.error_result(
                error=f"Failed to validate GitHub token: {str(e)}",
            )

    def get_credentials(self) -> object:
        """Get the current GitHub credentials.

        Returns:
            Dictionary with token and user information
        """
        if not self.token:
            credentials = self._load_credentials()
            if credentials and credentials.get("token"):
                self.token = credentials.get("token")

        return {"token": self.token, "user_info": self._user_info}

    def save_credentials(self) -> bool:
        """Save GitHub credentials to file.

        Returns:
            True if credentials were saved, False otherwise
        """
        return self._save_token_data(self.token)

    def _load_credentials(self) -> dict[str, Any] | None:
        """Load GitHub credentials from file.

        Returns:
            Dictionary with credentials or None if loading failed
        """
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
        """Save token data to credentials file.

        Args:
            token: GitHub token to save

        Returns:
            True if the token was saved, False otherwise
        """
        if not token or not self.credentials_file:
            return False

        # Ensure directory exists
        self._ensure_credentials_directory()

        # Prepare credentials data
        credentials = {"token": token, "saved_at": int(time.time())}

        if self._user_info:
            credentials["user_info"] = self._user_info

        # Write credentials to file
        result = fs.write_json(self.credentials_file, credentials, atomic=True)
        return result.success
