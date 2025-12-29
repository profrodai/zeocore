# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/mocks/requests.py
# role: tests
# neighbors: __init__.py, base.py, credentials.py, download.py, media.py, resources.py (+1 more)
# exports: MockDriveRequest
# git_branch: refactor/toolkitWorkflow
# git_commit: 0f9247b
# === QV-LLM:END ===

"""
Mock request objects for Google Drive testing.
"""

from typing import TypeVar
from unittest.mock import Mock

from quack_core.integrations.google.drive.protocols import DriveRequest

R = TypeVar("R")  # Generic type for return values


class MockDriveRequest(DriveRequest[R]):
    """Mock request object with configurable response."""

    def __init__(self, return_value: R, error: Exception | None = None):
        """
        Initialize a mock request with a return value or error.

        Args:
            return_value: Value to return on execute()
            error: Exception to raise on execute(), if any
        """
        # Create a comprehensive mock object with all potential attributes
        mock = Mock()

        # Configure execute method
        if error:
            mock.execute.side_effect = error
        else:
            mock.execute.return_value = return_value or {}

        # Add common attributes that might be expected
        mock.uri = "https://www.googleapis.com/drive/v3/files/mock-file-id?alt=media"
        mock.headers = {"Content-Type": "application/octet-stream"}

        # Add HTTP-related attributes
        class MockHttp:
            def request(self, *args, **kwargs):
                return mock, mock

        mock.http = MockHttp()
        mock.request = mock.http.request

        # Add _body attribute
        mock._body = {}

        # Ensure all protocol methods are present
        def default_method(*args, **kwargs):
            return mock

        # Add fallback methods to prevent attribute errors
        mock.get = default_method
        mock.create = default_method
        mock.list = default_method
        mock.update = default_method
        mock.delete = default_method
        mock.media = default_method
        mock.get_media = default_method

        self.mock = mock
        self.return_value = return_value
        self.error = error
        self.call_count = 0

    def __getattr__(self, name):
        """
        Dynamically add attributes as needed.

        This allows the mock to have any attribute without
        explicitly defining them.
        """
        return getattr(self.mock, name)

    def execute(self) -> R:
        """
        Execute the request and return the result or raise configured error.

        Returns:
            The configured return value

        Raises:
            Exception: The configured error, if any
        """
        self.call_count += 1
        return self.mock.execute()
