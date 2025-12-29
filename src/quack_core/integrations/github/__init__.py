"""GitHub integration for quack_core."""

from __future__ import annotations

from .auth import GitHubAuthProvider
from .client import GitHubClient
from .config import GitHubConfigProvider
from .models import GitHubRepo, GitHubUser, PullRequest, PullRequestStatus
from .protocols import GitHubIntegrationProtocol
from .service import GitHubIntegration

__all__ = [
    # Main classes
    "GitHubIntegration",
    "GitHubClient",
    "GitHubAuthProvider",
    "GitHubConfigProvider",
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
    """
    Create and return a GitHub integration instance.

    This function is the entry point for integration loading.

    Returns:
        GitHubIntegration instance
    """
    return GitHubIntegration()