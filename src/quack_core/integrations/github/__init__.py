# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/__init__.py
# module: quack_core.integrations.github.__init__
# role: module
# neighbors: service.py, models.py, protocols.py, config.py, auth.py, client.py
# exports: GitHubIntegration, GitHubClient, GitHubAuthProvider, GitHubConfigProvider, GitHubIntegrationProtocol, GitHubRepo, GitHubUser, PullRequest (+2 more)
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

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
