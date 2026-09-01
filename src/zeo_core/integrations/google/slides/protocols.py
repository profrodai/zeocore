"""
Protocol definitions for Google Slides integration.

This module defines protocol classes for the Google Slides service and
resource shape, ensuring proper typing throughout the codebase and avoiding
the use of Any -- mirrors `google/docs/protocols.py`'s structure, adapted
to the Slides v1 REST surface this integration actually calls
(presentations().get/create/batchUpdate). Per RULING-408 DESIGN-04, Slides
gets exactly these 3 of its 5 methods -- `create`, `get`, `batchUpdate`,
omitting both thumbnail-generation methods (`pages.getThumbnail` and any
page-level thumbnail surface) -- no escape-hatch method (that is a
separate, not-yet-built ruling item for the shared workspace surface).
"""

from typing import Any, Protocol, TypeVar, runtime_checkable

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.core.results import IntegrationResult

T = TypeVar("T")  # Generic type for result content
R = TypeVar("R", covariant=True)  # Generic type for return values


@runtime_checkable
class SlidesRequest(Protocol[R]):
    """Protocol for Google Slides request objects."""

    def execute(self) -> R:
        """
        Execute the request.

        Returns:
            R: The API response.
        """
        ...


@runtime_checkable
class SlidesPresentationsResource(Protocol):
    """Protocol for the Google Slides `presentations` resource."""

    def get(self, presentationId: str) -> SlidesRequest[dict[str, object]]:  # noqa: N803 -- matches the real googleapiclient parameter name verbatim
        """
        Get a presentation by ID.

        Args:
            presentationId: ID of the presentation to retrieve.

        Returns:
            SlidesRequest: Request object for getting the presentation.
        """
        ...

    def create(self, body: dict[str, object]) -> SlidesRequest[dict[str, object]]:
        """
        Create a new presentation.

        Args:
            body: Presentation resource body (e.g. `{"title": ...}`).

        Returns:
            SlidesRequest: Request object for creating the presentation.
        """
        ...

    def batchUpdate(  # noqa: N802 -- matches the real googleapiclient method name verbatim
        self,
        presentationId: str,  # noqa: N803 -- matches the real googleapiclient parameter name verbatim
        body: dict[str, object],
    ) -> SlidesRequest[dict[str, object]]:
        """
        Apply a batch of update requests to a presentation.

        Args:
            presentationId: ID of the presentation to update.
            body: `{"requests": [...]}` payload.

        Returns:
            SlidesRequest: Request object for applying the batch update.
        """
        ...


@runtime_checkable
class SlidesService(Protocol):
    """Protocol for the Google Slides API service (the object
    `googleapiclient.discovery.build("slides", "v1", ...)` returns)."""

    def presentations(self) -> SlidesPresentationsResource:
        """
        Get the presentations resource.

        Returns:
            SlidesPresentationsResource: The presentations resource.
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
class SlidesIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for the Google Slides integration's public surface.

    Built following `docs/protocols.py`'s `DocsIntegrationProtocol`
    precedent: a `@runtime_checkable` Protocol subclassing
    `IntegrationProtocol`. Per RULING-408, the curated surface is exactly
    the 3 Slides API methods (`get_presentation`, `create_presentation`,
    `batch_update`) -- no index-free convenience methods layered on top,
    unlike Docs: Slides' hazard is ORDER preservation, not index
    invalidation, so there is no analogous "never requires a caller-
    supplied index" convenience method to build here. See
    `request_builder.py`'s module docstring for the full contrast with
    Docs.
    """

    def get_presentation(
        self, presentation_id: str
    ) -> IntegrationResult[dict[str, Any]]:
        """Retrieve a presentation by ID (wraps `presentations.get`)."""
        ...

    def create_presentation(self, title: str) -> IntegrationResult[dict[str, Any]]:
        """Create a new, empty presentation with the given title."""
        ...

    def batch_update(
        self, presentation_id: str, requests: list[dict[str, Any]]
    ) -> IntegrationResult[dict[str, Any]]:
        """Apply a batch of update requests to a presentation (wraps
        `presentations.batchUpdate`), preserving caller order exactly --
        see `request_builder.py` for why this is the opposite policy from
        Docs' `batch_update`."""
        ...
