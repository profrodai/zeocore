# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/mocks/base.py
# role: tests
# neighbors: __init__.py, credentials.py, download.py, media.py, requests.py, resources.py (+1 more)
# exports: GenericApiRequestMock
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

"""
Base mock classes and utilities for Google Drive testing.
"""

from typing import TypeVar
from unittest.mock import Mock, PropertyMock

from googleapiclient.errors import HttpError

T = TypeVar("T")  # Generic type for content
R = TypeVar("R")  # Generic type for return values


class GenericApiRequestMock:
    """
    A dynamic mock that can simulate various API request objects
    with configurable behaviors.
    """

    def __init__(self, return_value=None, error=None, status=200, reason="OK"):
        """
        Create a mock API request object.

        Args:
            return_value: Value to return on execute
            error: Optional error to raise
            status: HTTP status code
            reason: HTTP status reason
        """
        # Create a comprehensive mock object
        self.mock = Mock()

        # Configure execute method
        if error:
            # Create an HttpError if an error is specified
            response = Mock()
            type(response).status = PropertyMock(return_value=status)
            type(response).reason = PropertyMock(return_value=reason)

            http_error = HttpError(resp=response, content=str(error).encode("utf-8"))
            self.mock.execute.side_effect = http_error
        else:
            # Set return value for successful execution
            self.mock.execute.return_value = return_value or {}

        # Add common attributes that might be expected
        self.mock.http = Mock()
        self.mock.request = Mock()
        self.mock.uri = "https://example.com/mock"
        self.mock.headers = {}

        # Add a method to simulate API calls
        def request_method(*args, **kwargs):
            return self.mock, self.mock

        self.mock.request.execute = self.mock.execute
        self.mock.http.request = request_method

    def __getattr__(self, name):
        """
        Dynamically add attributes as needed.

        This allows the mock to have any attribute without
        explicitly defining them.
        """
        attr = Mock()
        setattr(self.mock, name, attr)
        return attr

    def __call__(self, *args, **kwargs):
        """
        Make the mock callable to simulate various API methods.
        """
        return self.mock
