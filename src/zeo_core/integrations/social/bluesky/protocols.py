"""Protocol for the Bluesky integration."""

from typing import Protocol, runtime_checkable

from zeo_core.integrations.core import IntegrationProtocol, IntegrationResult

from .facets import LinkSpan, MentionSpan


@runtime_checkable
class BlueskyIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for the Bluesky integration."""

    def post(
        self,
        text: str,
        links: list[LinkSpan] | None = None,
        mentions: list[MentionSpan] | None = None,
    ) -> IntegrationResult[dict[str, object]]:
        """Create a post on Bluesky."""
        ...
