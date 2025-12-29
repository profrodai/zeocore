# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/utils/test_utils_api.py
# role: utils
# neighbors: __init__.py, test_utils_query.py
# exports: TestDriveUtilsApi
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
Tests for Google Drive api api module.
"""

from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from quack_core.lib.errors import QuackApiError
from quack_core.integrations.google.drive.utils import api
from tests.test_integrations.google.drive.mocks import (
    MockDriveRequest,
    create_mock_drive_service,
)


class TestDriveUtilsApi:
    """Tests for Google Drive api api functions."""

    def test_execute_api_request_success(self) -> None:
        """Test successful execution of an API request."""
        # Create a mock request using our MockDriveRequest
        mock_request = MockDriveRequest({"id": "file123"})

        # Test successful execution
        result = api.execute_api_request(
            mock_request, "Failed to execute request", "test.method"
        )

        assert result == {"id": "file123"}
        assert mock_request.call_count == 1  # Our mock tracks the call count

    def test_execute_api_request_http_error(self) -> None:
        """Test error handling for HttpError."""
        # Create mock response for HttpError
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.reason = "Bad Request"

        # Create the HttpError
        http_error = HttpError(mock_response, b"Error content")

        # Create a mock request with error
        mock_request = MockDriveRequest(None, http_error)

        # Test error handling
        with pytest.raises(QuackApiError) as excinfo:
            api.execute_api_request(
                mock_request, "Failed to execute request", "test.method"
            )

        assert "Failed to execute request" in str(excinfo.value)
        assert excinfo.value.service == "Google Drive"
        assert excinfo.value.api_method == "test.method"
        assert excinfo.value.original_error == http_error
        assert mock_request.call_count == 1  # Verify the request was executed

    def test_execute_api_request_generic_error(self) -> None:
        """Test error handling for generic errors."""
        # Create a generic error
        error = ValueError("Invalid value")

        # Create a mock request with the error
        mock_request = MockDriveRequest(None, error)

        # Test error handling
        with pytest.raises(QuackApiError) as excinfo:
            api.execute_api_request(
                mock_request, "Failed to execute request", "test.method"
            )

        assert "Failed to execute request" in str(excinfo.value)
        assert excinfo.value.service == "Google Drive"
        assert excinfo.value.api_method == "test.method"
        assert excinfo.value.original_error == error
        assert mock_request.call_count == 1  # Verify the request was executed

    def test_with_exponential_backoff_success(self) -> None:
        """Test the exponential backoff decorator with successful execution."""
        # Create a mock function
        mock_func = MagicMock()
        mock_func.return_value = "success"

        # Apply the decorator
        decorated_func = api.with_exponential_backoff(mock_func)

        # Test successful execution
        result = decorated_func("arg1", arg2="value2")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", arg2="value2")

    def test_with_exponential_backoff_retry(self) -> None:
        """Test the exponential backoff decorator with retries."""
        # Create a mock function that fails with HttpError twice, then succeeds
        mock_func = MagicMock()

        # Create HttpError responses
        mock_response1 = MagicMock()
        mock_response1.status = 429  # Too Many Requests
        http_error1 = HttpError(mock_response1, b"Rate limit exceeded")

        mock_response2 = MagicMock()
        mock_response2.status = 503  # Service Unavailable
        http_error2 = HttpError(mock_response2, b"Service unavailable")

        mock_func.side_effect = [http_error1, http_error2, "success"]

        # Apply the decorator with shortened delays for testing
        decorated_func = api.with_exponential_backoff(
            mock_func, max_retries=3, initial_delay=0.01, max_delay=0.05
        )

        # Mock sleep to avoid actual delays
        with patch("time.sleep") as mock_sleep:
            # Test retry behavior
            result = decorated_func("arg1", arg2="value2")

            assert result == "success"
            assert mock_func.call_count == 3
            assert mock_sleep.call_count == 2

            # Check that backoff increases
            assert mock_sleep.call_args_list[0][0][0] == 0.01  # First delay
            assert mock_sleep.call_args_list[1][0][0] == 0.02  # Second delay (doubled)

    def test_with_exponential_backoff_max_retries(self) -> None:
        """Test the exponential backoff decorator with max retries exceeded."""
        # Create a mock function that always fails with HttpError
        mock_func = MagicMock()

        # Create HttpError response
        mock_response = MagicMock()
        mock_response.status = 429  # Too Many Requests
        http_error = HttpError(mock_response, b"Rate limit exceeded")

        mock_func.side_effect = http_error

        # Apply the decorator with shortened delays for testing
        decorated_func = api.with_exponential_backoff(
            mock_func, max_retries=2, initial_delay=0.01, max_delay=0.05
        )

        # Mock sleep to avoid actual delays
        with patch("time.sleep") as mock_sleep:
            # Test max retries behavior
            with pytest.raises(HttpError) as excinfo:
                decorated_func("arg1", arg2="value2")

            assert excinfo.value == http_error
            assert mock_func.call_count == 3  # Initial call + 2 retries
            assert mock_sleep.call_count == 2

    def test_with_exponential_backoff_non_retryable_error(self) -> None:
        """Test the exponential backoff decorator with non-retryable errors."""
        # Create a mock function that fails with HttpError with non-retryable status
        mock_func = MagicMock()

        # Create HttpError response with 400 Bad Request (not retryable)
        mock_response = MagicMock()
        mock_response.status = 400
        http_error = HttpError(mock_response, b"Bad request")

        mock_func.side_effect = http_error

        # Apply the decorator
        decorated_func = api.with_exponential_backoff(mock_func)

        # Test non-retryable error behavior
        with pytest.raises(HttpError) as excinfo:
            decorated_func("arg1", arg2="value2")

        assert excinfo.value == http_error
        mock_func.assert_called_once()  # Should not retry

    def test_with_exponential_backoff_generic_error(self) -> None:
        """Test the exponential backoff decorator with generic errors."""
        # Create a mock function that fails with a generic error
        mock_func = MagicMock()
        error = ValueError("Invalid value")
        mock_func.side_effect = error

        # Apply the decorator
        decorated_func = api.with_exponential_backoff(mock_func)

        # Test generic error behavior
        with pytest.raises(ValueError) as excinfo:
            decorated_func("arg1", arg2="value2")

        assert excinfo.value == error
        mock_func.assert_called_once()  # Should not retry

    def test_execute_api_request_with_real_service(self) -> None:
        """Test execute_api_request with a complex mock service structure."""
        # Create a mock Drive service
        mock_service = create_mock_drive_service(
            fileId="test123",
            file_metadata={
                "id": "test123",
                "name": "test.txt",
                "mimeType": "text/plain",
            },
        )

        # Test the execute_api_request with a file get operation
        files_resource = mock_service.files()
        get_request = files_resource.get(fileId="test123", fields="id,name,mimeType")

        # Execute the request using the utility function
        result = api.execute_api_request(
            get_request, "Failed to get file metadata", "files.get"
        )

        # Verify the result
        assert result["id"] == "test123"
        assert result["name"] == "test.txt"
        assert result["mimeType"] == "text/plain"

        # Verify the request was executed
        assert isinstance(get_request, MockDriveRequest)
        assert get_request.call_count == 1
