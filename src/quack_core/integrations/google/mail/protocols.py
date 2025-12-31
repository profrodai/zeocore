# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/protocols.py
# module: quack_core.integrations.google.mail.protocols
# role: protocols
# neighbors: __init__.py, service.py, config.py
# exports: GoogleCredentials, GmailRequest, GmailAttachmentsResource, GmailMessagesResource, GmailUsersResource, GmailService
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
Protocol definitions for Gmail integration.

This module defines protocol classes for Gmail services and resources,
ensuring proper typing throughout the codebase and avoiding the use of Any.
"""

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")  # Generic type for result content
R = TypeVar("R")  # Generic type for return values


@runtime_checkable
class GoogleCredentials(Protocol):
    """Protocol for Google API credentials."""

    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]


@runtime_checkable
class GmailRequest(Protocol[R]):
    """Protocol for Gmail request objects."""

    def execute(self) -> R:
        """
        Execute the request.

        Returns:
            R: The API response.
        """
        ...


@runtime_checkable
class GmailAttachmentsResource(Protocol):
    """Protocol for Gmail attachments resource."""

    def get(
        self, user_id: str, message_id: str, attachment_id: str
    ) -> GmailRequest[dict[str, object]]:
        """
        Get an attachment.

        Args:
            user_id: Gmail user ID.
            message_id: Message ID.
            attachment_id: Attachment ID.

        Returns:
            GmailRequest: Request object for getting an attachment.
        """
        ...


@runtime_checkable
class GmailMessagesResource(Protocol):
    """Protocol for Gmail messages resource."""

    def list(
        self, user_id: str, q: str, max_results: int
    ) -> GmailRequest[dict[str, list[dict[str, object]]]]:
        """
        List messages.

        Args:
            user_id: Gmail user ID.
            q: Query string.
            max_results: Maximum number of results.

        Returns:
            GmailRequest: Request object for listing messages.
        """
        ...

    def get(
        self, user_id: str, message_id: str, message_format: str
    ) -> GmailRequest[dict[str, object]]:
        """
        Get a message.

        Args:
            user_id: Gmail user ID.
            message_id: Message ID.
            message_format: Message format.

        Returns:
            GmailRequest: Request object for getting a message.
        """
        ...

    def attachments(self) -> GmailAttachmentsResource:
        """
        Get attachments resource.

        Returns:
            GmailAttachmentsResource: Attachments resource.
        """
        ...


@runtime_checkable
class GmailUsersResource(Protocol):
    """Protocol for Gmail users resource."""

    def messages(self) -> GmailMessagesResource:
        """
        Get messages resource.

        Returns:
            GmailMessagesResource: Messages resource.
        """
        ...


@runtime_checkable
class GmailService(Protocol):
    """Protocol for Gmail service."""

    def users(self) -> GmailUsersResource:
        """
        Get users resource.

        Returns:
            GmailUsersResource: Users resource.
        """
        ...
