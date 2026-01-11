# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/_ops/test_email.py
# role: _ops
# neighbors: __init__.py, test_attachments.py, test_auth.py
# exports: TestGmailEmailOperations
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Tests for Gmail email _ops.

This module tests the email _ops functionality for the Google Mail integration,
including building queries, listing emails, and downloading emails.
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError
from quack_core.integrations.google.mail.operations import email
from quack_core.integrations.google.mail.protocols import (
    GmailAttachmentsResource,
    GmailMessagesResource,
    GmailRequest,
    GmailService,
    GmailUsersResource,
)


class TestGmailEmailOperations:
    """Tests for Gmail email _ops."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Create a protocol-compatible mock Gmail service."""

        # Create a proper mock hierarchy that matches the protocol structure
        class MockRequest(GmailRequest):
            def __init__(self, return_value):
                self.return_value = return_value

            def execute(self):
                return self.return_value

        class MockAttachmentsResource(GmailAttachmentsResource):
            def __init__(self):
                self.get_return = None
                # Initialize instance attributes in __init__
                self.last_user_id = None
                self.last_message_id = None
                self.last_attachment_id = None

            def get(
                self, user_id: str, message_id: str, attachment_id: str
            ) -> GmailRequest:
                # Store the parameters for test assertions
                self.last_user_id = user_id
                self.last_message_id = message_id
                self.last_attachment_id = attachment_id
                return MockRequest(self.get_return)

        class MockMessagesResource(GmailMessagesResource):
            def __init__(self):
                self.attachments_resource = MockAttachmentsResource()
                self.list_return = {}
                self.get_return = {}
                # Initialize attributes for test assertions
                self.last_user_id = None
                self.last_query = None
                self.last_max_results = None
                self.last_message_id = None
                self.last_format = None

            def list(self, user_id: str, q: str, max_results: int) -> GmailRequest:
                # Store parameters for test assertions
                self.last_user_id = user_id
                self.last_query = q
                self.last_max_results = max_results
                return MockRequest(self.list_return)

            def get(
                self, user_id: str, message_id: str, message_format: str
            ) -> GmailRequest:
                # Store parameters for test assertions
                self.last_user_id = user_id
                self.last_message_id = message_id
                self.last_format = message_format
                return MockRequest(self.get_return)

            def attachments(self) -> GmailAttachmentsResource:
                return self.attachments_resource

        class MockUsersResource(GmailUsersResource):
            def __init__(self):
                self.messages_resource = MockMessagesResource()

            def messages(self) -> GmailMessagesResource:
                return self.messages_resource

        class MockGmailService(GmailService):
            def __init__(self):
                self.users_resource = MockUsersResource()

            def users(self) -> GmailUsersResource:
                return self.users_resource

        # Create an instance of our protocol-compatible mock
        return MockGmailService()

    def test_build_query(self) -> None:
        """Test building Gmail search query."""
        # Test with days_back
        with patch(
            "quack_core.integrations.google.mail._ops.email.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime(2023, 1, 10)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            query = email.build_query(days_back=7)
            assert "after:2023/01/03" in query

        # Test with labels
        query = email.build_query(days_back=7, labels=["INBOX", "UNREAD"])
        assert "label:INBOX" in query
        assert "label:UNREAD" in query
        assert "after:" in query

        # Test with empty labels
        query = email.build_query(days_back=7, labels=[])
        assert "label:" not in query
        assert "after:" in query

        # Test with None labels
        query = email.build_query(days_back=7, labels=None)
        assert "label:" not in query
        assert "after:" in query

    def test_extract_header(self) -> None:
        """Test extracting headers from email."""
        headers = [
            {"name": "Subject", "value": "Test Email"},
            {"name": "From", "value": "sender@example.com"},
            {"name": "To", "value": "recipient@example.com"},
        ]

        # Test existing header
        subject = email._extract_header(headers, "subject", "No Subject")
        assert subject == "Test Email"

        # Test case insensitive
        from_header = email._extract_header(headers, "FROM", "Unknown")
        assert from_header == "sender@example.com"

        # Test missing header
        cc = email._extract_header(headers, "cc", "No CC")
        assert cc == "No CC"

        # Test empty headers
        empty_result = email._extract_header([], "subject", "Empty")
        assert empty_result == "Empty"

    def test_clean_filename(self) -> None:
        """Test cleaning filenames."""
        # Test basic cleaning
        clean = email.clean_filename("Test Email Subject!")
        assert clean == "test-email-subject"

        # Test with special characters
        clean = email.clean_filename("Re: [Important] Meeting Notes (2023/01/15)")
        assert clean == "re-important-meeting-notes-2023-01-15"

        # Test with email addresses
        clean = email.clean_filename("From: user@example.com")
        assert clean == "from-user-example-com"

        # Test with multiple spaces and special chars
        clean = email.clean_filename("  Weird   @#$%^   Filename  ")
        assert clean == "weird-filename"

        # Test empty string
        clean = email.clean_filename("")
        assert clean == ""

    def test_list_emails(self, mock_gmail_service) -> None:
        """Test listing emails."""
        logger = logging.getLogger("test_gmail")

        # Set up mock response for list operation
        messages_list = [
            {"id": "msg1", "threadId": "thread1"},
            {"id": "msg2", "threadId": "thread2"},
        ]

        mock_gmail_service.users().messages().list_return = {"messages": messages_list}

        # Mock execute_api_request to return the response directly
        with patch(
            "quack_core.integrations.google.mail._ops.email.execute_api_request",
            return_value={"messages": messages_list},
        ):
            # Test successful listing
            result = email.list_emails(mock_gmail_service, "me", "is:unread", logger)
            assert result.success is True
            assert len(result.content) == 2
            assert result.content[0]["id"] == "msg1"
            assert result.content[1]["threadId"] == "thread2"

        # Test with HttpError
        with patch(
            "quack_core.integrations.google.mail._ops.email.execute_api_request",
            side_effect=HttpError(
                resp=MagicMock(status=403), content=b"Permission denied"
            ),
        ):
            result = email.list_emails(mock_gmail_service, "me", "is:unread", logger)
            assert result.success is False
            assert "Gmail API error" in result.error

        # Test with generic exception
        with patch(
            "quack_core.integrations.google.mail._ops.email.execute_api_request",
            side_effect=Exception("Unexpected error"),
        ):
            result = email.list_emails(mock_gmail_service, "me", "is:unread", logger)
            assert result.success is False
            assert "Failed to list emails" in result.error

    def test_get_message_with_retry(self, mock_gmail_service) -> None:
        """Test getting a message with retry logic."""
        logger = logging.getLogger("test_gmail")

        # Mock execute_api_request to return a message
        with patch(
            "quack_core.integrations.google.mail._ops.email.execute_api_request",
            return_value={"id": "msg1", "snippet": "Test email"},
        ):
            message = email._get_message_with_retry(
                mock_gmail_service, "me", "msg1", 3, 0.1, 0.5, logger
            )
            assert message is not None
            assert message["id"] == "msg1"
            assert message["snippet"] == "Test email"

        # Test with retry
        mock_execute = MagicMock(
            side_effect=[
                HttpError(resp=MagicMock(status=500), content=b"Server error"),
                {"id": "msg1", "snippet": "Test email"},
            ]
        )
        with patch(
            "quack_core.integrations.google.mail._ops.email.execute_api_request",
            mock_execute,
        ):
            with patch(
                "quack_core.integrations.google.mail._ops.email.time.sleep"
            ) as mock_sleep:
                message = email._get_message_with_retry(
                    mock_gmail_service, "me", "msg1", 3, 0.1, 0.5, logger
                )
                assert message is not None
                assert message["id"] == "msg1"
                assert mock_execute.call_count == 2
                mock_sleep.assert_called_once_with(0.1)  # Initial delay

        # Test with max retries exceeded
        # Use a more explicit approach to mock the consecutive exceptions
        error_resp = MagicMock()
        error_resp.status = 500

        # Create a function that always raises HTTPError with our mock response
        def raise_http_error(*args, **kwargs):
            raise HttpError(resp=error_resp, content=b"Server error")

        # Create a mock with this side effect
        mock_execute = MagicMock(side_effect=raise_http_error)

        with patch(
            "quack_core.integrations.google.mail._ops.email.execute_api_request",
            mock_execute,
        ):
            with patch(
                "quack_core.integrations.google.mail._ops.email.time.sleep"
            ) as mock_sleep:
                # We're testing with 2 max retries, so expect 1 sleep call (after the 1st failure)
                message = email._get_message_with_retry(
                    mock_gmail_service, "me", "msg1", 2, 0.1, 0.5, logger
                )

                # Verify expected behavior
                assert message is None  # Should return None after exhausting retries
                assert mock_execute.call_count == 2  # Called twice (initial + 1 retry)
                assert mock_sleep.call_count == 1  # Only 1 sleep between the 2 attempts

    @patch("quack_core.integrations.google.mail._ops.email.process_message_parts")
    @patch(
        "quack_core.integrations.google.mail._ops.email._get_message_with_retry"
    )
    def test_download_email(
        self,
        mock_get_message: MagicMock,
        mock_process_parts: MagicMock,
        mock_gmail_service,
    ) -> None:
        """Test downloading an email."""
        logger = logging.getLogger("test_gmail")
        storage_path = "/path/to/storage"
        expected_file_path = (
            "/path/to/storage/2023-01-15-103000-sender-example-com.html"
        )

        # Mock message retrieval
        mock_get_message.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Email"},
                    {"name": "From", "value": "sender@example.com"},
                ],
                "parts": [{"mimeType": "text/html"}],
            },
        }

        # Mock message processing
        mock_process_parts.return_value = (
            "<html><body>Test content</body></html>",
            ["/path/to/storage/attachment.pdf"],
        )

        # Patch the filesystem write operation to avoid real filesystem access
        with (
            patch(
                "quack_core.integrations.google.mail._ops.email.datetime"
            ) as mock_dt,
            patch(
                "quack_core.integrations.google.mail._ops.email.clean_filename"
            ) as mock_clean,
            patch("quack_core.integrations.google.mail._ops.email.standalone") as mock_fs,
        ):
            # Set up date/time to ensure consistent filename generation
            mock_dt.now.return_value = datetime(2023, 1, 15, 10, 30, 0)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Configure filename cleaning
            mock_clean.return_value = "sender-example-com"

            # Configure fs join_path to return a string path
            mock_fs.join_path.return_value = expected_file_path

            # Configure fs write_text operation results
            write_result = MagicMock()
            write_result.success = True
            write_result.content = expected_file_path
            mock_fs.write_text.return_value = write_result

            # Test successful download
            result = email.download_email(
                mock_gmail_service,
                "me",
                "msg1",
                storage_path,
                True,
                True,
                3,
                0.1,
                0.5,
                logger,
            )

            # Verify results
            assert result.success is True
            assert expected_file_path == result.content
            assert "Email downloaded successfully" in result.message

            # Verify correct calls were made
            mock_get_message.assert_called_once_with(
                mock_gmail_service, "me", "msg1", 3, 0.1, 0.5, logger
            )

            # Verify that fs.join_path was called with the right arguments
            mock_fs.join_path.assert_called_once_with(
                storage_path, "2023-01-15-103000-sender-example-com.html"
            )

            # Verify that fs.write_text was called with the expected content
            write_content = mock_fs.write_text.call_args[0][1]
            assert "<h1>Subject: Test Email</h1>" in write_content
            assert "<h2>From: sender@example.com</h2>" in write_content
            assert "<html><body>Test content</body></html>" in write_content

        # Test with missing message
        mock_get_message.return_value = None
        result = email.download_email(
            mock_gmail_service,
            "me",
            "msg1",
            storage_path,
            False,
            False,
            3,
            0.1,
            0.5,
            logger,
        )
        assert result.success is False
        assert "Message msg1 could not be retrieved" in result.error

        # Test with no HTML content
        mock_get_message.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [{"name": "Subject", "value": "Test Email"}],
                "parts": [{"mimeType": "text/plain"}],
            },
        }
        mock_process_parts.return_value = (None, ["/path/to/storage/attachment.pdf"])
        result = email.download_email(
            mock_gmail_service,
            "me",
            "msg1",
            storage_path,
            False,
            False,
            3,
            0.1,
            0.5,
            logger,
        )
        assert result.success is False
        assert "No HTML content found in message msg1" in result.error

        # Test with exception
        mock_get_message.side_effect = Exception("Unexpected error")
        result = email.download_email(
            mock_gmail_service,
            "me",
            "msg1",
            storage_path,
            False,
            False,
            3,
            0.1,
            0.5,
            logger,
        )
        assert result.success is False
        assert "Failed to download email msg1" in result.error
