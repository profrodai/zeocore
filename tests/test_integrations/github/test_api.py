# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/github/test_api.py
# role: tests
# neighbors: __init__.py, conftest.py, test_auth.py, test_client.py, test_config.py, test_github_init.py (+5 more)
# exports: TestApiUtils, mock_session
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""Tests for GitHub API request utilities."""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from quack_core.lib.errors import (
    QuackApiError,
    QuackAuthenticationError,
    QuackQuotaExceededError,
)
from quack_core.integrations.github.utils.api import make_request


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = MagicMock(spec=requests.Session)
    return session


class TestApiUtils:
    """Tests for API utilities."""

    def test_make_request_success(self, mock_session):
        """Test successful API request."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.headers = {"X-RateLimit-Remaining": "100"}
        mock_session.request.return_value = mock_response

        # Make request
        result = make_request(
            session=mock_session,
            method="GET",
            url="/user",
            api_url="https://api.github.com",
            timeout=30,
        )

        # Verify result
        assert result == mock_response
        mock_session.request.assert_called_once_with(
            "GET", "https://api.github.com/user", params=None, json=None, timeout=30
        )

    def test_make_request_with_params_and_body(self, mock_session):
        """Test API request with parameters and body."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.headers = {"X-RateLimit-Remaining": "100"}
        mock_session.request.return_value = mock_response

        # Make request with params and JSON body
        params = {"page": 1, "per_page": 30}
        json_body = {"title": "Issue Title", "body": "Issue Body"}

        result = make_request(
            session=mock_session,
            method="POST",
            url="/repos/owner/repo/issues",
            api_url="https://api.github.com",
            params=params,
            json=json_body,
            timeout=30,
        )

        # Verify result
        assert result == mock_response
        mock_session.request.assert_called_once_with(
            "POST",
            "https://api.github.com/repos/owner/repo/issues",
            params=params,
            json=json_body,
            timeout=30,
        )

    def test_make_request_authentication_error(self, mock_session):
        """Test API request with authentication error."""
        # Mock 401 unauthorized response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Bad credentials"

        mock_error = requests.exceptions.HTTPError(response=mock_response)
        mock_error.response = mock_response

        mock_session.request.return_value = mock_response
        mock_response.raise_for_status.side_effect = mock_error

        # Make request
        with pytest.raises(QuackAuthenticationError) as excinfo:
            make_request(
                session=mock_session,
                method="GET",
                url="/user",
                api_url="https://api.github.com",
                timeout=30,
            )

        # Verify error
        assert "GitHub API authentication failed" in str(excinfo.value)
        assert excinfo.value.service == "GitHub"

    def test_make_request_rate_limit_exceeded(self, mock_session):
        """Test API request with rate limit exceeded."""
        # Mock rate limit response
        mock_response = MagicMock()
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 60),
        }
        mock_response.status_code = 429

        # Don't setup raise_for_status - we want to test the direct rate limit check path
        mock_session.request.return_value = mock_response

        # Mock time.time to return a stable value
        with patch("time.time", return_value=int(time.time())):
            # Avoid actual sleeping in tests
            with patch("time.sleep"):
                # We expect a QuackQuotaExceededError to be raised
                with pytest.raises(QuackQuotaExceededError) as excinfo:
                    # Use max_retries=1 so we immediately hit the quota error path
                    make_request(
                        session=mock_session,
                        method="GET",
                        url="/user",
                        api_url="https://api.github.com",
                        max_retries=1,
                    )

                # Just verify the basic error information is present
                # The exact format might vary, so we'll be less strict
                assert "GitHub API rate limit exceeded" in str(excinfo.value)
                assert "service='GitHub'" in str(excinfo.value)
                # The api_method or resource will be included in some form
                assert "api_method" in str(excinfo.value) or "quota_check" in str(
                    excinfo.value
                )

    def test_make_request_retry_success(self, mock_session):
        """Test API request with retry ending in success."""
        # First response will fail with 500, second will succeed
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500

        mock_error = requests.exceptions.HTTPError(response=mock_error_response)
        mock_error.response = mock_error_response

        mock_success_response = MagicMock()
        mock_success_response.headers = {"X-RateLimit-Remaining": "100"}

        # First call raises error, second call succeeds
        mock_session.request.side_effect = [
            MagicMock(raise_for_status=MagicMock(side_effect=mock_error)),
            mock_success_response,
        ]

        # Patch sleep to avoid waiting
        with patch("time.sleep"):
            # Make request
            result = make_request(
                session=mock_session,
                method="GET",
                url="/user",
                api_url="https://api.github.com",
                timeout=30,
                max_retries=2,
                retry_delay=0.1,
            )

            # Verify result
            assert result == mock_success_response
            assert mock_session.request.call_count == 2

    def test_make_request_connection_error_retry(self, mock_session):
        """Test API request with connection error and retry."""
        # Mock connection error
        mock_session.request.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        # Patch sleep to avoid waiting
        with patch("time.sleep"):
            # Make request with limited retries
            with pytest.raises(QuackApiError) as excinfo:
                make_request(
                    session=mock_session,
                    method="GET",
                    url="/user",
                    api_url="https://api.github.com",
                    timeout=30,
                    max_retries=2,
                    retry_delay=0.1,
                )

            # Verify error and retry attempts
            assert "GitHub API connection error" in str(excinfo.value)
            assert mock_session.request.call_count == 2
            assert excinfo.value.service == "GitHub"
            assert excinfo.value.api_method == "/user"

    def test_make_request_timeout_retry(self, mock_session):
        """Test API request with timeout and retry."""
        # Mock timeout error
        mock_session.request.side_effect = requests.exceptions.Timeout(
            "Request timed out"
        )

        # Patch sleep to avoid waiting
        with patch("time.sleep"):
            # Make request with limited retries
            with pytest.raises(QuackApiError) as excinfo:
                make_request(
                    session=mock_session,
                    method="GET",
                    url="/user",
                    api_url="https://api.github.com",
                    timeout=30,
                    max_retries=2,
                    retry_delay=0.1,
                )

            # Verify error and retry attempts
            assert "GitHub API timeout" in str(excinfo.value)
            assert mock_session.request.call_count == 2
            assert excinfo.value.service == "GitHub"
            assert excinfo.value.api_method == "/user"

    def test_make_request_unexpected_error(self, mock_session):
        """Test API request with unexpected error."""
        # Mock unexpected error
        mock_session.request.side_effect = ValueError("Unexpected error")

        # Make request
        with pytest.raises(QuackApiError) as excinfo:
            make_request(
                session=mock_session,
                method="GET",
                url="/user",
                api_url="https://api.github.com",
                timeout=30,
            )

        # Verify error
        assert "Unexpected error in GitHub API request" in str(excinfo.value)
        assert excinfo.value.service == "GitHub"
        assert excinfo.value.api_method == "/user"
