# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/__init__.py
# module: quack_core.integrations.github.__init__
# role: module
# neighbors: service.py, models.py, protocols.py, config.py, auth.py, client.py
# exports: GitHubIntegration, GitHubClient, GitHubAuthProvider, GitHubConfigProvider, GitHubTeachingAdapter, GitHubGrader, GitHubIntegrationProtocol, GitHubRepo (+4 more)
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""GitHub integration for quack_core."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from quack_core.integrations.core import registry

from .auth import GitHubAuthProvider
from .client import GitHubClient
from .config import GitHubConfigProvider
from .models import GitHubRepo, GitHubUser, PullRequest, PullRequestStatus
from .protocols import GitHubIntegrationProtocol
from .service import GitHubIntegration

# For type checkers only, import the quackster-related classes so they appear defined.
if TYPE_CHECKING:
    from quackster.github.grading import GitHubGrader
    from quackster.github.teaching_adapter import GitHubTeachingAdapter

__all__ = [
    # Main classes
    "GitHubIntegration",
    "GitHubClient",
    "GitHubAuthProvider",
    "GitHubConfigProvider",
    "GitHubTeachingAdapter",  # Provided lazily below
    "GitHubGrader",  # Provided lazily below
    # Protocols
    "GitHubIntegrationProtocol",
    # Models
    "GitHubRepo",
    "GitHubUser",
    "PullRequest",
    "PullRequestStatus",
    # Factory function
    "create_integration",
]


def create_integration() -> GitHubIntegration:
    """Create and return a GitHub integration instance.

    Returns:
        GitHubIntegration instance
    """
    return GitHubIntegration()


def __getattr__(name: str) -> Any:
    """Lazily load quackster-related classes to avoid circular imports.

    Args:
        name: Attribute name to load

    Returns:
        The requested module or class

    Raises:
        AttributeError: If the requested attribute doesn't exist
    """
    if name == "GitHubGrader":
        from quackster.github.grading import GitHubGrader

        return GitHubGrader
    elif name == "GitHubTeachingAdapter":
        from quackster.github.teaching_adapter import GitHubTeachingAdapter

        return GitHubTeachingAdapter
    else:
        raise AttributeError(
            f"module 'quack_core.integrations.github' has no attribute '{name}'"
        )


# Automatically register the integration
try:
    integration = create_integration()

    # Try to register the integration using the standard method
    try:
        # Check what methods are available in the registry
        registry_methods = dir(registry)

        # Try to find a registration method
        if hasattr(registry, "register"):
            registry.register(integration)
        elif hasattr(registry, "add_integration"):
            registry.add_integration(integration)
        else:
            # If we can't find any registration method, log a warning
            logger = logging.getLogger(__name__)
            logger.warning(
                "Unable to register GitHub integration: no suitable registry method found"
            )
    except (AttributeError, TypeError) as e:
        # If registration fails, log a warning
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to register GitHub integration: {str(e)}")
except Exception as e:
    logging.getLogger(__name__).error(
        f"Failed to register GitHub integration: {str(e)}"
    )
