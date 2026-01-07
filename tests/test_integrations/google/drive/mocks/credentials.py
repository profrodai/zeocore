# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/mocks/credentials.py
# role: tests
# neighbors: __init__.py, base.py, download.py, media.py, requests.py, resources.py (+1 more)
# exports: MockGoogleCredentials, create_credentials
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Mock credential objects for Google Drive testing.
"""

from quack_core.integrations.google.drive.protocols import GoogleCredentials


class MockGoogleCredentials(GoogleCredentials):
    """Mock Google credentials for authentication testing."""

    def __init__(
        self,
        token: str = "test_token",
        refresh_token: str = "refresh_token",
        token_uri: str = "https://oauth2.googleapis.com/token",
        client_id: str = "client_id",
        client_secret: str = "client_secret",
        scopes: list[str] | None = None,
    ):
        """
        Initialize mock Google credentials.

        Args:
            token: The access token
            refresh_token: The refresh token
            token_uri: The token URI
            client_id: The client ID
            client_secret: The client secret
            scopes: The OAuth scopes
        """
        self.token = token
        self.refresh_token = refresh_token
        self.token_uri = token_uri
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or ["https://www.googleapis.com/auth/drive.file"]

    def authorize(self, http):
        """
        Authorize an httplib2.Http instance with these credentials.

        Args:
            http: An httplib2.Http instance to authorize.

        Returns:
            The authorized http object.
        """
        # Just return the http object unchanged, as we're just mocking
        return http


def create_credentials() -> GoogleCredentials:
    """
    Create mock Google credentials for testing.

    Returns:
        Mock credentials that conform to the GoogleCredentials protocol
    """
    return MockGoogleCredentials()
