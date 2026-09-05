"""Bluesky integration for zeo_core.

Post to Bluesky via the AT Protocol, authenticating with a pasted **app
password** (Settings > App Passwords on bsky.app -- never the main account
password; no OAuth, no developer app, no approval). Follows the same shape
as `integrations.notion` and `integrations.github` -- a config provider, an
auth provider, a thin HTTP client wrapper, and a service class implementing
`BlueskyIntegrationProtocol` -- and registers under the
`zeo_core.integrations` entry-point group the same way (see this repo's
`pyproject.toml`, `[project.entry-points."zeo_core.integrations"]`, key
`social.bluesky`).

This is the first connector in the `integrations.social` package
(RULING-409 s6c: greenfield, no `social/` package existed before this),
built first specifically because it needs neither of the two blockers
RULING-409 identified for the six connectors after it: no shared OAuth2
helper (`integrations/core/oauth2.py`, not built here -- Bluesky has no
OAuth flow to exercise it) and no fresh-directory config defect (this
service defers all config/credential resolution into `initialize()`,
matching `mail/service.py`'s already-correct pattern rather than
`drive`/`calendar`'s eager `__init__` resolution).

Quickstart::

    from zeo_core.integrations.social.bluesky import BlueskyIntegration

    bluesky = BlueskyIntegration()  # reads BLUESKY_IDENTIFIER /
                                     # BLUESKY_APP_PASSWORD from the
                                     # environment, or a saved credentials
                                     # file from a prior session
    result = bluesky.initialize()
    assert result.success

    posted = bluesky.post("Hello from zeocore!")
    assert posted.success  # 2xx accepted -- NOT visibility; see RULING-409 s5

    # With a link facet (client-side byte-offset computation, RULING-409 s6c):
    from zeo_core.integrations.social.bluesky import LinkSpan

    posted = bluesky.post(
        "Check out zeocore: https://github.com/profrodai/zeocore",
        links=[
            LinkSpan(
                text="https://github.com/profrodai/zeocore",
                uri="https://github.com/profrodai/zeocore",
            )
        ],
    )

Every call returns an `IntegrationResult[T]` (`.success`, `.content`,
`.error`) -- see `zeo_core.integrations.core.results`.

**What this package does NOT do** (RULING-409 s6b/s6c, binding on this
SOW): does not build `integrations/core/oauth2.py` (Bluesky has no OAuth
flow); does not implement scheduling (that seam sits above the provider);
does not port Postiz's `postPending`/`checkPostStatus`/`finalizePost`,
Temporal error classes, `maxConcurrentJob`/`refreshCron`/`taskQueue`, or any
UI -- all Temporal/Prisma-coupled and out of scope for a stateless library.
"""

from __future__ import annotations

from .auth import BlueskyAuthProvider
from .client import BlueskyAPIError, BlueskyClient
from .config import BlueskyConfigProvider
from .facets import LinkSpan, MentionSpan, compute_facets
from .protocols import BlueskyIntegrationProtocol
from .service import BlueskyIntegration

__all__ = [
    # Main classes
    "BlueskyIntegration",
    "BlueskyClient",
    "BlueskyAuthProvider",
    "BlueskyConfigProvider",
    # Protocols
    "BlueskyIntegrationProtocol",
    # Rich-text facets
    "LinkSpan",
    "MentionSpan",
    "compute_facets",
    # Errors
    "BlueskyAPIError",
    # Factory function
    "create_integration",
]


def create_integration() -> BlueskyIntegration:
    """
    Create and return a Bluesky integration instance.

    This function is the entry point for integration loading.

    Returns:
        BlueskyIntegration instance
    """
    return BlueskyIntegration()
