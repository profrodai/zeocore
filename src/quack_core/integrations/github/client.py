# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/client.py
# module: quack_core.integrations.github.client
# role: module
# neighbors: __init__.py, service.py, models.py, protocols.py, config.py, auth.py
# exports: GitHubClient
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===

"""GitHub API client for quack_core."""

from typing import Any, Literal

import requests
from quack_core.lib.logging import get_logger

from .models import GitHubRepo, GitHubUser, PullRequest
from .operations import (
    add_issue_comment,
    check_repository_exists,
    create_issue,
    create_pull_request,
    fork_repo,
    get_issue,
    get_pull_request,
    get_pull_request_files,  # Added import
    get_repo,
    get_repository_file_content,
    get_user,
    is_repo_starred,
    list_issues,
    list_pull_requests,
    star_repo,
    unstar_repo,
    update_repository_file,
)

logger = get_logger(__name__)


class GitHubClient:
    """Client for interacting with the GitHub API."""

    def __init__(
        self,
        token: str,
        api_url: str = "https://api.github.com",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the GitHub client.

        Args:
            token: GitHub personal access token
            api_url: GitHub API URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for requests
            retry_delay: Delay between retries in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Set up session with default headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "QuackCore-GitHub-Integration",
            }
        )

        # Cache for user info
        self._current_user: GitHubUser | None = None

    def get_user(self, username: str | None = None) -> GitHubUser:
        """Get information about a GitHub user.

        Args:
            username: GitHub username. If None, gets the authenticated user.

        Returns:
            GitHubUser object

        Raises:
            QuackApiError: If the API request fails
            QuackAuthenticationError: If authentication fails
        """
        if username is None:
            # Get authenticated user
            if self._current_user:
                return self._current_user

        user = get_user(
            session=self.session,
            api_url=self.api_url,
            username=username,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

        # Cache the current user
        if username is None:
            self._current_user = user

        return user

    def get_repo(self, full_name: str) -> GitHubRepo:
        """Get information about a GitHub repository.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            GitHubRepo object

        Raises:
            QuackApiError: If the API request fails
        """
        return get_repo(
            session=self.session,
            full_name=full_name,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def star_repo(self, full_name: str) -> bool:
        """Star a GitHub repository.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            True if successful

        Raises:
            QuackApiError: If the API request fails
        """
        return star_repo(
            session=self.session,
            full_name=full_name,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def unstar_repo(self, full_name: str) -> bool:
        """Unstar a GitHub repository.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            True if successful

        Raises:
            QuackApiError: If the API request fails
        """
        return unstar_repo(
            session=self.session,
            full_name=full_name,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def is_repo_starred(self, full_name: str) -> bool:
        """Check if a repository is starred by the authenticated user.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            True if the repo is starred, False otherwise
        """
        return is_repo_starred(
            session=self.session,
            full_name=full_name,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def fork_repo(self, full_name: str, organization: str | None = None) -> GitHubRepo:
        """Fork a GitHub repository.

        Args:
            full_name: Full repository name (owner/repo)
            organization: Optional organization name to fork to

        Returns:
            GitHubRepo object for the new fork

        Raises:
            QuackApiError: If the API request fails
        """
        return fork_repo(
            session=self.session,
            full_name=full_name,
            api_url=self.api_url,
            organization=organization,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def create_pull_request(
        self,
        base_repo: str,
        head: str,
        title: str,
        body: str | None = None,
        base_branch: str = "main",
    ) -> PullRequest:
        """Create a pull request.

        Args:
            base_repo: Full name of the base repository (owner/repo)
            head: Head reference in the format "username:branch"
            title: Pull request title
            body: Pull request body
            base_branch: Base branch to merge into

        Returns:
            PullRequest object

        Raises:
            QuackApiError: If the API request fails
        """
        return create_pull_request(
            session=self.session,
            base_repo=base_repo,
            head=head,
            title=title,
            api_url=self.api_url,
            body=body,
            base_branch=base_branch,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def list_pull_requests(
        self,
        repo: str,
        state: Literal["open", "closed", "all"] = "open",
        author: str | None = None,
    ) -> list[PullRequest]:
        """List pull requests for a repository.

        Args:
            repo: Full repository name (owner/repo)
            state: Pull request state (open, closed, all)
            author: Filter by author username

        Returns:
            List of PullRequest objects

        Raises:
            QuackApiError: If the API request fails
        """
        return list_pull_requests(
            session=self.session,
            repo=repo,
            api_url=self.api_url,
            state=state,
            author=author,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def get_pull_request(self, repo: str, number: int) -> PullRequest:
        """Get a specific pull request.

        Args:
            repo: Full repository name (owner/repo)
            number: Pull request number

        Returns:
            PullRequest object

        Raises:
            QuackApiError: If the API request fails
        """
        return get_pull_request(
            session=self.session,
            repo=repo,
            number=number,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def check_repository_exists(self, full_name: str) -> bool:
        """Check if a repository exists.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            True if the repository exists, False otherwise
        """
        return check_repository_exists(
            session=self.session,
            full_name=full_name,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def get_repository_file_content(
        self, repo: str, path: str, ref: str | None = None
    ) -> tuple[str, str]:
        """Get the content of a file from a repository.

        Args:
            repo: Full repository name (owner/repo)
            path: Path to the file within the repository
            ref: Git reference (branch, tag, commit)

        Returns:
            Tuple of (content, sha)

        Raises:
            QuackApiError: If the API request fails
        """
        return get_repository_file_content(
            session=self.session,
            repo=repo,
            path=path,
            api_url=self.api_url,
            ref=ref,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def update_repository_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        sha: str,
        branch: str | None = None,
    ) -> bool:
        """Update a file in a repository.

        Args:
            repo: Full repository name (owner/repo)
            path: Path to the file within the repository
            content: New file content
            message: Commit message
            sha: Current file SHA
            branch: Branch to commit to

        Returns:
            True if successful

        Raises:
            QuackApiError: If the API request fails
        """
        return update_repository_file(
            session=self.session,
            repo=repo,
            path=path,
            content=content,
            message=message,
            sha=sha,
            api_url=self.api_url,
            branch=branch,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    # Issue methods

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an issue in a repository.

        Args:
            repo: Full repository name (owner/repo)
            title: Issue title
            body: Issue body
            labels: List of labels to apply
            assignees: List of users to assign

        Returns:
            Issue data dictionary

        Raises:
            QuackApiError: If the API request fails
        """
        return create_issue(
            session=self.session,
            repo=repo,
            title=title,
            api_url=self.api_url,
            body=body,
            labels=labels,
            assignees=assignees,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def list_issues(
        self,
        repo: str,
        state: Literal["open", "closed", "all"] = "open",
        labels: str | None = None,
        sort: Literal["created", "updated", "comments"] = "created",
        direction: Literal["asc", "desc"] = "desc",
    ) -> list[dict[str, Any]]:
        """List issues in a repository.

        Args:
            repo: Full repository name (owner/repo)
            state: Issue state (open, closed, all)
            labels: Comma-separated list of label names
            sort: What to sort results by
            direction: Direction to sort

        Returns:
            List of issue data dictionaries

        Raises:
            QuackApiError: If the API request fails
        """
        return list_issues(
            session=self.session,
            repo=repo,
            api_url=self.api_url,
            state=state,
            labels=labels,
            sort=sort,
            direction=direction,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def get_issue(self, repo: str, issue_number: int) -> dict[str, Any]:
        """Get a specific issue in a repository.

        Args:
            repo: Full repository name (owner/repo)
            issue_number: Issue number

        Returns:
            Issue data dictionary

        Raises:
            QuackApiError: If the API request fails
        """
        return get_issue(
            session=self.session,
            repo=repo,
            issue_number=issue_number,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def add_issue_comment(
        self, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Add a comment to an issue.

        Args:
            repo: Full repository name (owner/repo)
            issue_number: Issue number
            body: Comment body

        Returns:
            Comment data dictionary

        Raises:
            QuackApiError: If the API request fails
        """
        return add_issue_comment(
            session=self.session,
            repo=repo,
            issue_number=issue_number,
            body=body,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )

    def get_pull_request_files(
        self,
        repo: str,
        pull_number: int,
    ) -> list[dict[str, Any]]:
        """Get the files changed in a pull request.

        Args:
            repo: Full repository name (owner/repo)
            pull_number: Pull request number

        Returns:
            List of file information dictionaries

        Raises:
            QuackApiError: If the API request fails
        """
        return get_pull_request_files(
            session=self.session,
            repo=repo,
            pull_number=pull_number,
            api_url=self.api_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )
