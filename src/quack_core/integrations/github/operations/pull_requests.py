# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/operations/pull_requests.py
# module: quack_core.integrations.github.operations.pull_requests
# role: operations
# neighbors: __init__.py, issues.py, repositories.py, users.py
# exports: create_pull_request, list_pull_requests, get_pull_request, merge_pull_request, get_pull_request_files, add_pull_request_review, get_pull_requests_by_user
# git_branch: refactor/toolkitWorkflow
# git_commit: e4fa88d
# === QV-LLM:END ===

"""GitHub pull request _operations."""

from datetime import datetime
from typing import Any, Literal

import requests

from quack_core.lib.errors import QuackError
from quack_core.integrations.github.models import (
    GitHubUser,
    PullRequest,
    PullRequestStatus,
)
from quack_core.integrations.github.utils.api import make_request
from quack_core.lib.logging import get_logger

logger = get_logger(__name__)


def create_pull_request(
    session: requests.Session,
    base_repo: str,
    head: str,
    title: str,
    api_url: str,
    body: str | None = None,
    base_branch: str = "main",
    **request_kwargs: Any,
) -> PullRequest:
    """Create a pull request.

    Args:
        session: Requests session with authentication headers.
        base_repo: Full name of the base repository (owner/repo).
        head: Head reference in the format "username:branch".
        title: Pull request title.
        api_url: Base API URL.
        body: Pull request body.
        base_branch: Base branch to merge into.
        **request_kwargs: Additional request parameters.

    Returns:
        PullRequest object.

    Raises:
        QuackApiError: If the API request fails.
    """
    endpoint = f"/repos/{base_repo}/pulls"
    data = {"title": title, "head": head, "base": base_branch}
    if body:
        data["body"] = body

    response = make_request(
        session=session,
        method="POST",
        url=endpoint,
        api_url=api_url,
        json=data,
        **request_kwargs,
    )
    pr_data = response.json()

    # Extract author information.
    author_data = pr_data.get("user", {})
    author = GitHubUser(
        username=author_data.get("login"),
        url=author_data.get("html_url"),
        avatar_url=author_data.get("avatar_url"),
    )

    # Parse the dates.
    created_at = datetime.fromisoformat(
        pr_data.get("created_at").replace("Z", "+00:00")
    )
    updated_at = datetime.fromisoformat(
        pr_data.get("updated_at").replace("Z", "+00:00")
    )
    merged_at = None
    if pr_data.get("merged_at"):
        merged_at = datetime.fromisoformat(
            pr_data.get("merged_at").replace("Z", "+00:00")
        )

    # Determine the status.
    if merged_at:
        status = PullRequestStatus.MERGED
    elif pr_data.get("state") == "closed":
        status = PullRequestStatus.CLOSED
    else:
        status = PullRequestStatus.OPEN

    # Extract head and base repo full names.
    head_repo = pr_data.get("head", {}).get("repo", {}).get("full_name", "")
    base_repo_name = pr_data.get("base", {}).get("repo", {}).get("full_name", "")

    return PullRequest(
        number=pr_data.get("number"),
        title=pr_data.get("title"),
        url=pr_data.get("html_url"),
        author=author,
        status=status,
        body=pr_data.get("body"),
        created_at=created_at,
        updated_at=updated_at,
        merged_at=merged_at,
        base_repo=base_repo_name,
        head_repo=head_repo,
        base_branch=pr_data.get("base", {}).get("ref", ""),
        head_branch=pr_data.get("head", {}).get("ref", ""),
    )


def list_pull_requests(
    session: requests.Session,
    repo: str,
    api_url: str,
    state: Literal["open", "closed", "all"] = "open",
    author: str | None = None,
    **request_kwargs: Any,
) -> list[PullRequest]:
    """List pull requests for a repository.

    Args:
        session: Requests session with authentication headers.
        repo: Full repository name (owner/repo).
        api_url: Base API URL.
        state: Pull request state (open, closed, all).
        author: Filter by author username.
        **request_kwargs: Additional request parameters.

    Returns:
        List of PullRequest objects.

    Raises:
        QuackApiError: If the API request fails.
    """
    endpoint = f"/repos/{repo}/pulls"
    params = {"state": state}
    response = make_request(
        session=session,
        method="GET",
        url=endpoint,
        api_url=api_url,
        params=params,
        **request_kwargs,
    )
    pr_list = response.json()
    result = []

    for pr_data in pr_list:
        if author and pr_data.get("user", {}).get("login") != author:
            continue

        author_data = pr_data.get("user", {})
        author_obj = GitHubUser(
            username=author_data.get("login"),
            url=author_data.get("html_url"),
            avatar_url=author_data.get("avatar_url"),
        )
        created_at = datetime.fromisoformat(
            pr_data.get("created_at").replace("Z", "+00:00")
        )
        updated_at = datetime.fromisoformat(
            pr_data.get("updated_at").replace("Z", "+00:00")
        )
        merged_at = None
        if pr_data.get("merged_at"):
            merged_at = datetime.fromisoformat(
                pr_data.get("merged_at").replace("Z", "+00:00")
            )

        if merged_at:
            status = PullRequestStatus.MERGED
        elif pr_data.get("state") == "closed":
            status = PullRequestStatus.CLOSED
        else:
            status = PullRequestStatus.OPEN

        head_repo = pr_data.get("head", {}).get("repo", {}).get("full_name", "")
        base_repo_name = pr_data.get("base", {}).get("repo", {}).get("full_name", "")

        pr = PullRequest(
            number=pr_data.get("number"),
            title=pr_data.get("title"),
            url=pr_data.get("html_url"),
            author=author_obj,
            status=status,
            body=pr_data.get("body"),
            created_at=created_at,
            updated_at=updated_at,
            merged_at=merged_at,
            base_repo=base_repo_name,
            head_repo=head_repo,
            base_branch=pr_data.get("base", {}).get("ref", ""),
            head_branch=pr_data.get("head", {}).get("ref", ""),
        )
        result.append(pr)

    return result


def get_pull_request(
    session: requests.Session,
    repo: str,
    number: int,
    api_url: str,
    **request_kwargs: Any,
) -> PullRequest:
    """Get a specific pull request.

    Args:
        session: Requests session with authentication headers.
        repo: Full repository name (owner/repo).
        number: Pull request number.
        api_url: Base API URL.
        **request_kwargs: Additional request parameters.

    Returns:
        PullRequest object.

    Raises:
        QuackApiError: If the API request fails.
    """
    endpoint = f"/repos/{repo}/pulls/{number}"
    response = make_request(
        session=session, method="GET", url=endpoint, api_url=api_url, **request_kwargs
    )
    pr_data = response.json()

    author_data = pr_data.get("user", {})
    author = GitHubUser(
        username=author_data.get("login"),
        url=author_data.get("html_url"),
        avatar_url=author_data.get("avatar_url"),
    )
    created_at = datetime.fromisoformat(
        pr_data.get("created_at").replace("Z", "+00:00")
    )
    updated_at = datetime.fromisoformat(
        pr_data.get("updated_at").replace("Z", "+00:00")
    )
    merged_at = None
    if pr_data.get("merged_at"):
        merged_at = datetime.fromisoformat(
            pr_data.get("merged_at").replace("Z", "+00:00")
        )

    if merged_at:
        status = PullRequestStatus.MERGED
    elif pr_data.get("state") == "closed":
        status = PullRequestStatus.CLOSED
    else:
        status = PullRequestStatus.OPEN

    head_repo = pr_data.get("head", {}).get("repo", {}).get("full_name", "")
    base_repo_name = pr_data.get("base", {}).get("repo", {}).get("full_name", "")

    return PullRequest(
        number=pr_data.get("number"),
        title=pr_data.get("title"),
        url=pr_data.get("html_url"),
        author=author,
        status=status,
        body=pr_data.get("body"),
        created_at=created_at,
        updated_at=updated_at,
        merged_at=merged_at,
        base_repo=base_repo_name,
        head_repo=head_repo,
        base_branch=pr_data.get("base", {}).get("ref", ""),
        head_branch=pr_data.get("head", {}).get("ref", ""),
    )


def merge_pull_request(
    session: requests.Session,
    repo: str,
    pull_number: int,
    api_url: str,
    commit_title: str | None = None,
    commit_message: str | None = None,
    merge_method: Literal["merge", "squash", "rebase"] = "merge",
    **request_kwargs: Any,
) -> bool:
    """Merge a pull request.

    Args:
        session: Requests session with authentication headers.
        repo: Full repository name (owner/repo).
        pull_number: Pull request number.
        api_url: Base API URL.
        commit_title: Title for the automatic commit.
        commit_message: Extra detail to append to commit message.
        merge_method: Merge method to use (merge, squash, rebase).
        **request_kwargs: Additional request parameters.

    Returns:
        True if the pull request was merged.

    Raises:
        QuackApiError: If the API request fails.
    """
    endpoint = f"/repos/{repo}/pulls/{pull_number}/merge"
    data = {"merge_method": merge_method}
    if commit_title:
        data["commit_title"] = commit_title
    if commit_message:
        data["commit_message"] = commit_message

    response = make_request(
        session=session,
        method="PUT",
        url=endpoint,
        api_url=api_url,
        json=data,
        **request_kwargs,
    )
    result = response.json()
    return result.get("merged", False)


def get_pull_request_files(
    session: requests.Session,
    repo: str,
    pull_number: int,
    api_url: str,
    **request_kwargs: Any,
) -> list[dict[str, Any]]:
    """Get the files changed in a pull request.

    Args:
        session: Requests session with authentication headers.
        repo: Full repository name (owner/repo).
        pull_number: Pull request number.
        api_url: Base API URL.
        **request_kwargs: Additional request parameters.

    Returns:
        List of file information dictionaries.

    Raises:
        QuackApiError: If the API request fails.
    """
    endpoint = f"/repos/{repo}/pulls/{pull_number}/files"
    response = make_request(
        session=session,
        method="GET",
        url=endpoint,
        api_url=api_url,
        **request_kwargs,
    )
    return response.json()


def add_pull_request_review(
    session: requests.Session,
    repo: str,
    pull_number: int,
    body: str,
    api_url: str,
    event: Literal["APPROVE", "REQUEST_CHANGES", "COMMENT"] = "COMMENT",
    **request_kwargs: Any,
) -> dict[str, Any]:
    """Add a review to a pull request.

    Args:
        session: Requests session with authentication headers.
        repo: Full repository name (owner/repo).
        pull_number: Pull request number.
        body: Review content.
        api_url: Base API URL.
        event: Review event (APPROVE, REQUEST_CHANGES, or COMMENT).
        **request_kwargs: Additional request parameters.

    Returns:
        Review data dictionary.

    Raises:
        QuackApiError: If the API request fails.
    """
    endpoint = f"/repos/{repo}/pulls/{pull_number}/reviews"
    data = {"body": body, "event": event}
    response = make_request(
        session=session,
        method="POST",
        url=endpoint,
        api_url=api_url,
        json=data,
        **request_kwargs,
    )
    return response.json()


def get_pull_requests_by_user(
    session: requests.Session,
    username: str,
    org: str,
    api_url: str,
    state: Literal["open", "closed", "all"] = "open",
    **request_kwargs: Any,
) -> list[PullRequest]:
    """
    Get pull requests created by a user within an organization.

    This function uses the GitHub Search API for issues with the query qualifiers:
    `is:pr`, `author:{username}`, and `org:{org}`. An optional state qualifier
    is added based on the state parameter.

    Args:
        session: Requests session with authentication headers.
        username: GitHub username.
        org: GitHub organization name.
        api_url: Base API URL.
        state: PR state filter (open, closed, or all).
        **request_kwargs: Additional request parameters.

    Returns:
        List of PullRequest objects.

    Raises:
        QuackError: If the API request fails.
    """
    query = f"is:pr author:{username} org:{org}"
    if state == "open":
        query += " is:open"
    elif state == "closed":
        query += " is:closed"

    endpoint = "/search/issues"
    params = {"q": query}

    try:
        response = make_request(
            session=session,
            method="GET",
            url=endpoint,
            api_url=api_url,
            params=params,
            **request_kwargs,
        )
    except Exception as e:
        msg = f"Failed to search for pull requests: {str(e)}"
        logger.error(msg)
        raise QuackError(msg, original_error=e)

    try:
        search_results = response.json()
    except Exception as e:
        msg = f"Failed to parse search results: {str(e)}"
        logger.error(msg)
        raise QuackError(msg, original_error=e)

    pr_list: list[PullRequest] = []
    for item in search_results.get("items", []):
        try:
            pr_number = item.get("number")
            title = item.get("title")
            html_url = item.get("html_url")
            body = item.get("body")
            state_str = item.get("state")
            status = (
                PullRequestStatus.OPEN
                if state_str == "open"
                else PullRequestStatus.CLOSED
            )

            user_data = item.get("user", {})
            author_obj = GitHubUser(
                username=user_data.get("login"),
                url=user_data.get("html_url"),
                avatar_url=user_data.get("avatar_url"),
            )

            created_at = datetime.fromisoformat(
                item.get("created_at").replace("Z", "+00:00")
            )
            updated_at = datetime.fromisoformat(
                item.get("updated_at").replace("Z", "+00:00")
            )

            pr = PullRequest(
                number=pr_number,
                title=title,
                url=html_url,
                author=author_obj,
                status=status,
                body=body,
                created_at=created_at,
                updated_at=updated_at,
                merged_at=None,
                base_repo="",
                head_repo="",
                base_branch="",
                head_branch="",
            )
            pr_list.append(pr)
        except Exception as e:
            logger.warning(f"Error processing search result item: {e}")
            continue

    return pr_list
