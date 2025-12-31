# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/mocks.py
# role: tests
# neighbors: __init__.py, test_mail.py, test_mail_service.py
# exports: MockGmailRequest, MockGmailAttachmentsResource, MockGmailMessagesResource, MockGmailUsersResource, MockGmailService, MockGoogleCredentials, MockRequest, create_mock_gmail_service (+2 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===

"""
Mock objects for Gmail service testing.

This module provides mock implementations of Gmail service objects
that can be used across different test modules.
"""

import base64
from typing import TypeVar, cast

from quack_core.integrations.google.mail.protocols import (
    GmailAttachmentsResource,
    GmailMessagesResource,
    GmailRequest,
    GmailService,
    GmailUsersResource,
    GoogleCredentials,
)

T = TypeVar("T")  # Generic type for content
R = TypeVar("R")  # Generic type for return values


class MockGmailRequest(GmailRequest[dict[str, T]]):
    """Mock request object with configurable response."""

    def __init__(self, return_value: dict[str, T], error: Exception | None = None):
        """
        Initialize a mock request with a return value or error.

        Args:
            return_value: Value to return on execute()
            error: Exception to raise on execute(), if any
        """
        self.return_value = return_value
        self.error = error

    def execute(self) -> dict[str, T]:
        """Execute the request and return the result or raise configured error."""
        if self.error:
            raise self.error
        return self.return_value


class MockGmailAttachmentsResource(GmailAttachmentsResource):
    """Mock attachments resource with configurable behavior."""

    def __init__(
        self, attachment_data: str | None = None, error: Exception | None = None
    ):
        """
        Initialize mock attachments resource.

        Args:
            attachment_data: Base64-encoded attachment data to return
            error: Exception to raise on API calls, if any
        """
        self.attachment_data = (
            attachment_data or base64.urlsafe_b64encode(b"attachment content").decode()
        )
        self.error = error

        # Tracking attributes for assertions
        self.last_user_id: str | None = None
        self.last_message_id: str | None = None
        self.last_attachment_id: str | None = None

    def get(
        self, user_id: str, message_id: str, attachment_id: str
    ) -> GmailRequest[dict[str, object]]:
        """
        Mock get method for retrieving an attachment.

        Args:
            user_id: The user ID
            message_id: The message ID
            attachment_id: The attachment ID

        Returns:
            A mock request that will return the attachment data
        """
        self.last_user_id = user_id
        self.last_message_id = message_id
        self.last_attachment_id = attachment_id

        return cast(
            GmailRequest[dict[str, object]],
            MockGmailRequest({"data": self.attachment_data}, self.error),
        )


class MockGmailMessagesResource(GmailMessagesResource):
    """Mock messages resource with configurable behavior."""

    def __init__(
        self,
        list_messages: list[dict[str, T]] | None = None,
        message_data: dict[str, T] | None = None,
        attachments_resource: GmailAttachmentsResource | None = None,
        list_error: Exception | None = None,
        get_error: Exception | None = None,
    ):
        """
        Initialize mock messages resource.

        Args:
            list_messages: Messages to return in list operation
            message_data: Message details to return in get operation
            attachments_resource: Mock attachments resource to use
            list_error: Exception to raise on list operation, if any
            get_error: Exception to raise on get operation, if any
        """
        self._attachments = attachments_resource or MockGmailAttachmentsResource()
        self.list_messages = list_messages or [
            {"id": "msg1", "threadId": "thread1"},
            {"id": "msg2", "threadId": "thread2"},
        ]
        self.message_data = message_data or {}
        self.list_error = list_error
        self.get_error = get_error

        # Tracking attributes for assertions
        self.last_user_id: str | None = None
        self.last_query: str | None = None
        self.last_max_results: int | None = None
        self.last_message_id: str | None = None
        self.last_format: str | None = None

    def attachments(self) -> GmailAttachmentsResource:
        """Return mock attachments resource."""
        return self._attachments

    def get(
        self, user_id: str, message_id: str, message_format: str = "full"
    ) -> GmailRequest[dict[str, object]]:
        """
        Mock get method for retrieving a message.

        Args:
            user_id: The user ID
            message_id: The message ID
            message_format: The format to return

        Returns:
            A mock request that will return the message data
        """
        self.last_user_id = user_id
        self.last_message_id = message_id
        self.last_format = message_format

        # Use provided message data or generate default
        if not self.message_data:
            message_data = {
                "id": message_id,
                "threadId": f"thread-{message_id}",
                "labelIds": ["INBOX"],
                "snippet": "Email snippet...",
                "payload": {
                    "mimeType": "multipart/mixed",
                    "headers": [
                        {"name": "From", "value": "sender@example.com"},
                        {"name": "To", "value": "recipient@example.com"},
                        {"name": "Subject", "value": f"Test Email {message_id}"},
                        {"name": "Date", "value": "Mon, 1 Jan 2023 12:00:00 +0000"},
                    ],
                    "parts": [
                        {
                            "mimeType": "text/html",
                            "body": {
                                "data": base64.urlsafe_b64encode(
                                    b"<html><body>Test Email Content</body></html>"
                                ).decode()
                            },
                        }
                    ],
                },
            }
        else:
            message_data = self.message_data

        return cast(
            GmailRequest[dict[str, object]],
            MockGmailRequest(message_data, self.get_error),
        )

    def list(
        self, user_id: str, q: str, max_results: int = 100
    ) -> GmailRequest[dict[str, list[dict[str, object]]]]:
        """
        Mock list method for listing messages.

        Args:
            user_id: The user ID
            q: The search query
            max_results: Maximum number of messages to return

        Returns:
            A mock request that will return the messages list
        """
        self.last_user_id = user_id
        self.last_query = q
        self.last_max_results = max_results

        # Customize response based on query
        if q and "subject:Error" in q:
            response = {"messages": []}
        else:
            response = {"messages": self.list_messages, "nextPageToken": None}

        return cast(
            GmailRequest[dict[str, list[dict[str, object]]]],
            MockGmailRequest(response, self.list_error),
        )


class MockGmailUsersResource(GmailUsersResource):
    """Mock users resource."""

    def __init__(self, messages_resource: GmailMessagesResource | None = None):
        """
        Initialize mock users resource.

        Args:
            messages_resource: Mock messages resource to use
        """
        self._messages = messages_resource or MockGmailMessagesResource()

    def messages(self) -> GmailMessagesResource:
        """Return mock messages resource."""
        return self._messages


class MockGmailService(GmailService):
    """Mock Gmail service for testing."""

    def __init__(self, users_resource: GmailUsersResource | None = None):
        """
        Initialize mock Gmail service.

        Args:
            users_resource: Mock users resource to use
        """
        self._users = users_resource or MockGmailUsersResource()

    def users(self) -> GmailUsersResource:
        """Return mock users resource."""
        return self._users


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
        self.scopes = scopes or ["https://www.googleapis.com/auth/gmail.readonly"]


def create_mock_gmail_service(
    attachment_data: str | None = None,
    message_data: dict[str, T] | None = None,
    list_messages: list[dict[str, T]] | None = None,
) -> GmailService:
    """
    Create and return a configurable mock Gmail service.

    Args:
        attachment_data: Base64-encoded attachment data to return
        message_data: Message details to return in get operation
        list_messages: Messages to return in list operation

    Returns:
        A mock Gmail service object cast to the GmailService type
    """
    attachments_resource = MockGmailAttachmentsResource(attachment_data)
    messages_resource = MockGmailMessagesResource(
        list_messages=list_messages,
        message_data=message_data,
        attachments_resource=attachments_resource,
    )
    users_resource = MockGmailUsersResource(messages_resource)
    return MockGmailService(users_resource)


def create_error_gmail_service(
    list_error: Exception | None = None,
    get_error: Exception | None = None,
    attachment_error: Exception | None = None,
) -> GmailService:
    """
    Create a Gmail service mock that raises configurable exceptions.

    Args:
        list_error: Exception to raise on list operation
        get_error: Exception to raise on get operation
        attachment_error: Exception to raise on attachment _operations

    Returns:
        A mock Gmail service object that will raise exceptions
    """
    if not list_error:
        list_error = Exception("API Error: Failed to list messages")
    if not get_error:
        get_error = Exception("API Error: Failed to get message")
    if not attachment_error:
        attachment_error = Exception("API Error: Failed to get attachment")

    attachments_resource = MockGmailAttachmentsResource(error=attachment_error)
    messages_resource = MockGmailMessagesResource(
        attachments_resource=attachments_resource,
        list_error=list_error,
        get_error=get_error,
    )
    users_resource = MockGmailUsersResource(messages_resource)
    return MockGmailService(users_resource)


def create_credentials() -> GoogleCredentials:
    """
    Create mock Google credentials for testing.

    Returns:
        Mock credentials that conform to the GoogleCredentials protocol
    """
    return MockGoogleCredentials()


class MockRequest(GmailRequest[R]):
    """
    A reusable implementation of GmailRequest protocol for testing API functions.

    This class can be used to create mock request objects that conform to the
    GmailRequest protocol and track their invocations.

    Example:
        # Create a request that returns a dictionary
        request = MockRequest({"id": "msg1", "payload": {}})

        # Create a request that raises an exception
        error_request = MockRequest(side_effect=ValueError("Test error"))
    """

    def __init__(
        self, return_value: R | None = None, side_effect: Exception | None = None
    ):
        """
        Initialize a mock request with a return value or error.

        Args:
            return_value: Value to return on execute()
            side_effect: Exception to raise on execute(), if any
        """
        self.return_value = return_value
        self.side_effect = side_effect
        self.call_count = 0

    def execute(self) -> R:
        """
        Execute the request and return the result or raise the configured error.

        This method tracks the number of times it's called for assertion purposes.

        Returns:
            The configured return value

        Raises:
            Exception: The configured side effect, if any
        """
        self.call_count += 1
        if self.side_effect:
            raise self.side_effect
        if self.return_value is None:
            raise ValueError("Return value not specified for MockRequest.execute()")
        return self.return_value
