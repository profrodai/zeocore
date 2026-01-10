# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/utils/test_api.py
# role: utils
# neighbors: __init__.py
# exports: TestGmailApiUtils
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

"""
Tests for Gmail API utility functions.

This module tests the API utilities for the Google Mail integration,
including request execution and exponential backoff.
"""

from typing import TypeVar
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError
from quack_core.integrations.google.mail.protocols import GmailRequest
from quack_core.integrations.google.mail.utils.api import (
    execute_api_request,
    with_exponential_backoff,
)
from quack_core.core.errors import QuackApiError

R = TypeVar("R")  # Generic type for return values


class TestGmailApiUtils:
    """Tests for Gmail API utilities."""

    def test_execute_api_request(self) -> None:
        """Test executing a Gmail API request."""

        # Create a mock that conforms to the GmailRequest protocol
        class MockGmailRequest(GmailRequest[dict[str, object]]):
            def __init__(self, return_value=None, side_effect=None):
                self.return_value = return_value
                self.side_effect = side_effect
                self.call_count = 0

            def execute(self) -> dict[str, object]:
                self.call_count += 1
                if self.side_effect:
                    raise self.side_effect
                return self.return_value

        # Test successful execution
        mock_request = MockGmailRequest(return_value={"id": "msg1", "payload": {}})

        result = execute_api_request(
            mock_request,
            "Failed to get message",
            "users.messages.get",
        )

        assert result == {"id": "msg1", "payload": {}}
        assert mock_request.call_count == 1

        # Test with HttpError
        resp = MagicMock()
        resp.status = 403
        http_error = HttpError(resp=resp, content=b"Permission denied")

        mock_request = MockGmailRequest(side_effect=http_error)

        with pytest.raises(QuackApiError) as excinfo:
            execute_api_request(
                mock_request,
                "Failed to get message",
                "users.messages.get",
            )

        assert "Failed to get message" in str(excinfo.value)
        assert "Permission denied" in str(excinfo.value)
        assert excinfo.value.api_method == "users.messages.get"

        # Test with generic exception
        generic_error = Exception("Unexpected error")
        mock_request = MockGmailRequest(side_effect=generic_error)

        with pytest.raises(QuackApiError) as excinfo:
            execute_api_request(
                mock_request,
                "Failed to get message",
                "users.messages.get",
            )

        assert "Failed to get message" in str(excinfo.value)
        assert "Unexpected error" in str(excinfo.value)
        assert excinfo.value.api_method == "users.messages.get"

    def test_with_exponential_backoff(self) -> None:
        """Test the exponential backoff decorator."""
        # Create a function that fails with HttpError a few times, then succeeds
        mock_func = MagicMock()

        # First 2 calls fail with status 429 (rate limit), third call succeeds
        resp1 = MagicMock()
        resp1.status = 429
        resp2 = MagicMock()
        resp2.status = 429

        mock_func.side_effect = [
            HttpError(resp=resp1, content=b"Rate limit exceeded"),
            HttpError(resp=resp2, content=b"Rate limit exceeded"),
            "success",
        ]

        # Apply the decorator
        decorated_func = with_exponential_backoff(
            mock_func,
            max_retries=3,
            initial_delay=0.01,  # Use small values for testing
            max_delay=0.05,
        )

        # Mock time.sleep to avoid actual delays
        with patch("time.sleep") as mock_sleep:
            result = decorated_func("arg1", arg2="value")

            assert result == "success"
            assert mock_func.call_count == 3
            assert mock_sleep.call_count == 2

            # Check backoff timing
            assert mock_sleep.call_args_list[0][0][0] == 0.01  # Initial delay
            assert mock_sleep.call_args_list[1][0][0] == 0.02  # Doubled delay

        # Test with non-retryable status code
        mock_func.reset_mock()
        resp = MagicMock()
        resp.status = 400  # Bad request - not retryable
        mock_func.side_effect = HttpError(resp=resp, content=b"Bad request")

        with pytest.raises(HttpError):
            decorated_func("arg1")

        assert mock_func.call_count == 1  # No retries for 400 error

        # Test with max retries exceeded
        mock_func.reset_mock()
        resp = MagicMock()
        resp.status = 503  # Service unavailable - retryable
        mock_func.side_effect = HttpError(resp=resp, content=b"Service unavailable")

        with pytest.raises(HttpError):
            decorated_func("arg1")

        assert mock_func.call_count == 4  # Original call + 3 retries

        # Test with non-HttpError exception
        mock_func.reset_mock()
        mock_func.side_effect = ValueError("Bad value")

        with pytest.raises(ValueError):
            decorated_func("arg1")

        assert mock_func.call_count == 1  # No retries for non-HttpError
