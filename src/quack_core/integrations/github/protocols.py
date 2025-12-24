# quack-core/src/quack_core/integrations/github/protocols.py
"""Protocols for GitHub integration."""

from typing import Protocol, runtime_checkable

from quack_core.integrations.core import IntegrationProtocol, IntegrationResult

from .models import GitHubRepo, GitHubUser, PullRequest


@runtime_checkable
class GitHubIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for GitHub integration."""

    def get_current_user(self) -> IntegrationResult[GitHubUser]:
        """Get the authenticated user."""
        ...

    def get_repo(self, full_name: str) -> IntegrationResult[GitHubRepo]:
        """Get a GitHub repository."""
        ...

    def star_repo(self, full_name: str) -> IntegrationResult[bool]:
        """Star a GitHub repository."""
        ...

    def fork_repo(self, full_name: str) -> IntegrationResult[GitHubRepo]:
        """Fork a GitHub repository."""
        ...

    def create_pull_request(
        self,
        base_repo: str,
        head: str,
        title: str,
        body: str | None = None,
        base_branch: str = "main",
    ) -> IntegrationResult[PullRequest]:
        """Create a pull request."""
        ...

    def list_pull_requests(
        self, repo: str, state: str = "open", author: str | None = None
    ) -> IntegrationResult[list[PullRequest]]:
        """List pull requests for a repository."""
        ...

    def get_pull_request(
        self, repo: str, number: int
    ) -> IntegrationResult[PullRequest]:
        """Get a specific pull request."""
        ...
