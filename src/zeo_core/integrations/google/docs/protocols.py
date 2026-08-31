"""
Protocol definitions for Google Docs integration.

This module defines protocol classes for the Google Docs service and
resource shape, ensuring proper typing throughout the codebase and avoiding
the use of Any -- mirrors `google/calendar/protocols.py`'s structure,
adapted to the Docs v1 REST surface this integration actually calls
(documents().get/create/batchUpdate). Per RULING-408 DESIGN-01, Docs gets
exactly these 3 methods -- no more, no less, and no escape-hatch method
(that is a separate, not-yet-built ruling item for the shared workspace
surface).
"""

from typing import Any, Protocol, TypeVar, runtime_checkable

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.core.results import IntegrationResult

T = TypeVar("T")  # Generic type for result content
R = TypeVar("R", covariant=True)  # Generic type for return values


@runtime_checkable
class DocsRequest(Protocol[R]):
    """Protocol for Google Docs request objects."""

    def execute(self) -> R:
        """
        Execute the request.

        Returns:
            R: The API response.
        """
        ...


@runtime_checkable
class DocsDocumentsResource(Protocol):
    """Protocol for the Google Docs `documents` resource."""

    def get(self, documentId: str) -> DocsRequest[dict[str, object]]:  # noqa: N803 -- matches the real googleapiclient parameter name verbatim
        """
        Get a document by ID.

        Args:
            documentId: ID of the document to retrieve.

        Returns:
            DocsRequest: Request object for getting the document.
        """
        ...

    def create(self, body: dict[str, object]) -> DocsRequest[dict[str, object]]:
        """
        Create a new document.

        Args:
            body: Document resource body (e.g. `{"title": ...}`).

        Returns:
            DocsRequest: Request object for creating the document.
        """
        ...

    def batchUpdate(  # noqa: N802 -- matches the real googleapiclient method name verbatim
        self,
        documentId: str,  # noqa: N803 -- matches the real googleapiclient parameter name verbatim
        body: dict[str, object],
    ) -> DocsRequest[dict[str, object]]:
        """
        Apply a batch of update requests to a document.

        Args:
            documentId: ID of the document to update.
            body: `{"requests": [...]}` payload.

        Returns:
            DocsRequest: Request object for applying the batch update.
        """
        ...


@runtime_checkable
class DocsService(Protocol):
    """Protocol for the Google Docs API service (the object
    `googleapiclient.discovery.build("docs", "v1", ...)` returns)."""

    def documents(self) -> DocsDocumentsResource:
        """
        Get the documents resource.

        Returns:
            DocsDocumentsResource: The documents resource.
        """
        ...


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
class DocsIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for the Google Docs integration's public surface.

    Built following `calendar/protocols.py`'s `CalendarIntegrationProtocol`
    precedent: a `@runtime_checkable` Protocol subclassing
    `IntegrationProtocol`. Per RULING-408, the curated surface is exactly
    the 3 Docs API methods (`get_document`, `create_document`,
    `batch_update`) plus the 2 index-free convenience methods built on top
    of `batch_update` (`replace_text`, `append_text`) and the plain-text
    extraction helper.
    """

    def get_document(self, document_id: str) -> IntegrationResult[dict[str, Any]]:
        """Retrieve a document by ID (wraps `documents.get`)."""
        ...

    def get_document_text(self, document_id: str) -> IntegrationResult[str]:
        """Retrieve a document and flatten its body to plain text."""
        ...

    def create_document(self, title: str) -> IntegrationResult[dict[str, Any]]:
        """Create a new, empty document with the given title."""
        ...

    def batch_update(
        self, document_id: str, requests: list[dict[str, Any]]
    ) -> IntegrationResult[dict[str, Any]]:
        """Apply a batch of update requests to a document (wraps
        `documents.batchUpdate`), reverse-sorted by index internally."""
        ...

    def replace_text(
        self,
        document_id: str,
        find: str,
        replace: str,
        match_case: bool = False,
    ) -> IntegrationResult[dict[str, Any]]:
        """Replace all occurrences of `find` with `replace` (index-free:
        matches by string via `replaceAllText`, never by offset)."""
        ...

    def append_text(
        self, document_id: str, text: str
    ) -> IntegrationResult[dict[str, Any]]:
        """Append `text` to the end of the document body (index-free: the
        caller never computes or passes a text index)."""
        ...
