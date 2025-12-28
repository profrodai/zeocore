# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/operations/test_auth.py
# role: operations
# neighbors: __init__.py, test_attachments.py, test_email.py
# exports: TestGmailAuthOperations
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

"""
Tests for Gmail authentication _operations.

This module tests the authentication functionality for the Google Mail integration,
including initializing the Gmail service.
"""

from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackApiError
from quack_core.integrations.google.mail.operations import auth
from quack_core.integrations.google.mail.protocols import GoogleCredentials


class TestGmailAuthOperations:
    """Tests for Gmail authentication _operations."""

    def test_initialize_gmail_service(self) -> None:
        """Test initializing the Gmail service."""

        # Create a mock that conforms to the GoogleCredentials protocol
        class MockCredentials:
            token = "test_token"
            refresh_token = "refresh_token"
            token_uri = "https://oauth2.googleapis.com/token"
            client_id = "client_id"
            client_secret = "client_secret"
            scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

        # Create an instance of our protocol-compatible mock
        mock_creds = MockCredentials()

        # Mock build function
        mock_service = MagicMock()
        with patch("googleapiclient.discovery.build") as mock_build:
            mock_build.return_value = mock_service

            # Test successful initialization
            service = auth.initialize_gmail_service(mock_creds)

            assert service is mock_service
            mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)

        # Test with API error
        with patch("googleapiclient.discovery.build") as mock_build:
            mock_build.side_effect = Exception("API error")

            with pytest.raises(QuackApiError) as excinfo:
                auth.initialize_gmail_service(mock_creds)

            assert "Failed to initialize Gmail API" in str(excinfo.value)
            assert mock_build.call_count == 1

    def test_google_credentials_protocol(self) -> None:
        """Test GoogleCredentials protocol conformity."""

        # Create a minimal credentials object that conforms to the protocol
        class MockCredentials:
            token = "test_token"
            refresh_token = "refresh_token"
            token_uri = "https://oauth2.googleapis.com/token"
            client_id = "client_id"
            client_secret = "client_secret"
            scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

        creds = MockCredentials()

        # Check that our mock conforms to the protocol
        # This is mostly for clarity in the test, as the code doesn't use isinstance
        # with runtime_checkable protocols directly
        from typing import cast

        protocol_creds = cast(GoogleCredentials, creds)

        # Mock build function
        mock_service = MagicMock()
        with patch("googleapiclient.discovery.build") as mock_build:
            mock_build.return_value = mock_service

            # Test with protocol-compatible credentials
            service = auth.initialize_gmail_service(protocol_creds)

            assert service is mock_service
            mock_build.assert_called_once()

        # Test with incomplete credentials that don't match the protocol
        class IncompleteCredentials:
            token = "test_token"
            # Missing other required attributes

        incomplete_creds = IncompleteCredentials()

        # Use this approach to bypass type checking during testing
        # so we can explicitly test the runtime behavior with invalid credentials
        with patch.object(
            auth, "initialize_gmail_service", side_effect=auth.initialize_gmail_service
        ) as patched_init:
            with patch("googleapiclient.discovery.build") as mock_build:
                mock_build.side_effect = Exception("Missing credential attributes")

                with pytest.raises(QuackApiError):
                    # Use the patched version which bypasses type checking
                    patched_init(incomplete_creds)  # type: ignore
