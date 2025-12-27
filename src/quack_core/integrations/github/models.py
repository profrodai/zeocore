# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/models.py
# module: quack_core.integrations.github.models
# role: models
# neighbors: __init__.py, service.py, protocols.py, config.py, auth.py, client.py
# exports: PullRequestStatus, GitHubUser, GitHubRepo, PullRequest
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""GitHub integration data models for quack_core."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PullRequestStatus(str, Enum):
    """Status of a pull request."""

    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class GitHubUser(BaseModel):
    """Model representing a GitHub user."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    username: str = Field(description="GitHub username")
    url: HttpUrl = Field(description="GitHub profile URL")
    name: str | None = Field(
        default=None, description="User's full name if available"
    )
    email: str | None = Field(default=None, description="User's email if available")
    avatar_url: HttpUrl | None = Field(
        default=None, description="URL to user's avatar"
    )

    def __str__(self) -> str:
        """String representation of the user."""
        return self.username

    def __eq__(self, other: object) -> bool:
        """Custom equality method to handle string URL comparisons."""
        if isinstance(other, GitHubUser):
            return self.username == other.username and str(self.url) == str(other.url)
        elif isinstance(other, str):
            # Compare with string - allow comparing to URL string directly
            return other == str(self.url) or other == self.username
        return NotImplemented


class GitHubRepo(BaseModel):
    """Model representing a GitHub repository."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(description="Repository name without owner")
    full_name: str = Field(description="Full repository name with owner (owner/repo)")
    url: HttpUrl = Field(description="Repository URL")
    clone_url: HttpUrl = Field(description="Git clone URL")
    default_branch: str = Field(default="main", description="Default branch")
    description: str | None = Field(
        default=None, description="Repository description"
    )
    fork: bool = Field(default=False, description="Whether this repo is a fork")
    forks_count: int = Field(default=0, description="Number of forks")
    stargazers_count: int = Field(default=0, description="Number of stars")
    owner: GitHubUser = Field(description="Repository owner")

    def __str__(self) -> str:
        """String representation of the repository."""
        return self.full_name

    def __eq__(self, other: object) -> bool:
        """Custom equality method to handle string URL comparisons."""
        if isinstance(other, GitHubRepo):
            return self.full_name == other.full_name and str(self.url) == str(other.url)
        elif isinstance(other, str):
            # Compare with string - allow comparing to URL string directly
            return other == str(self.url) or other == self.full_name
        return NotImplemented


class PullRequest(BaseModel):
    """Model representing a GitHub pull request."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    number: int = Field(description="Pull request number")
    title: str = Field(description="Pull request title")
    url: HttpUrl = Field(description="Pull request URL")
    author: GitHubUser = Field(description="Pull request author")
    status: PullRequestStatus = Field(description="Pull request status")
    body: str | None = Field(default=None, description="Pull request body")
    created_at: datetime = Field(description="Pull request creation date")
    updated_at: datetime = Field(description="Last update date")
    merged_at: datetime | None = Field(
        default=None, description="Merge date if merged"
    )
    base_repo: str = Field(description="Base repository full name")
    head_repo: str = Field(description="Head repository full name")
    base_branch: str = Field(description="Base branch")
    head_branch: str = Field(description="Head branch")

    def __str__(self) -> str:
        """String representation of the pull request."""
        return f"{self.base_repo}#{self.number}"

    def __eq__(self, other: object) -> bool:
        """Custom equality method to handle string URL comparisons."""
        if isinstance(other, PullRequest):
            return self.number == other.number and str(self.url) == str(other.url)
        elif isinstance(other, str):
            # Compare with string - allow comparing to URL string directly
            return other == str(self.url)
        return NotImplemented
