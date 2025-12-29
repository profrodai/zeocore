# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/operations/repositories.py
# module: quack_core.integrations.github.operations.repositories
# role: operations
# neighbors: __init__.py, issues.py, pull_requests.py, users.py
# exports: get_repo, star_repo, unstar_repo, is_repo_starred, fork_repo, check_repository_exists, get_repository_file_content, update_repository_file
# git_branch: refactor/toolkitWorkflow
# git_commit: 21647d6
# === QV-LLM:END ===

"""GitHub repository _operations."""

import base64
from typing import Any

import requests
from quack_core.integrations.github.models import GitHubRepo, GitHubUser
from quack_core.integrations.github.utils.api import make_request
from quack_core.lib.errors import QuackApiError


def get_repo(
    session: requests.Session, full_name: str, api_url: str, **request_kwargs: Any
) -> GitHubRepo:
    """Get information about a GitHub repository.

    Args:
        session: Requests session with authentication headers
        full_name: Full repository name (owner/repo)
        api_url: Base API URL
        **request_kwargs: Additional request parameters

    Returns:
        GitHubRepo object

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/repos/{full_name}"
    response = make_request(
        session=session, method="GET", url=endpoint, api_url=api_url, **request_kwargs
    )

    repo_data = response.json()

    # Extract owner information
    owner_data = repo_data.get("owner", {})
    owner = GitHubUser(
        username=owner_data.get("login"),
        url=owner_data.get("html_url"),
        avatar_url=owner_data.get("avatar_url"),
    )

    # Create and return the repository object
    return GitHubRepo(
        name=repo_data.get("name"),
        full_name=repo_data.get("full_name"),
        url=repo_data.get("html_url"),
        clone_url=repo_data.get("clone_url"),
        default_branch=repo_data.get("default_branch"),
        description=repo_data.get("description"),
        fork=repo_data.get("fork", False),
        forks_count=repo_data.get("forks_count", 0),
        stargazers_count=repo_data.get("stargazers_count", 0),
        owner=owner,
    )


def star_repo(
    session: requests.Session, full_name: str, api_url: str, **request_kwargs: Any
) -> bool:
    """Star a GitHub repository.

    Args:
        session: Requests session with authentication headers
        full_name: Full repository name (owner/repo)
        api_url: Base API URL
        **request_kwargs: Additional request parameters

    Returns:
        True if successful

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/user/starred/{full_name}"
    make_request(
        session=session, method="PUT", url=endpoint, api_url=api_url, **request_kwargs
    )
    return True


def unstar_repo(
    session: requests.Session, full_name: str, api_url: str, **request_kwargs: Any
) -> bool:
    """Unstar a GitHub repository.

    Args:
        session: Requests session with authentication headers
        full_name: Full repository name (owner/repo)
        api_url: Base API URL
        **request_kwargs: Additional request parameters

    Returns:
        True if successful

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/user/starred/{full_name}"
    make_request(
        session=session,
        method="DELETE",
        url=endpoint,
        api_url=api_url,
        **request_kwargs,
    )
    return True


def is_repo_starred(
    session: requests.Session, full_name: str, api_url: str, **request_kwargs: Any
) -> bool:
    """Check if a repository is starred by the authenticated user.

    Args:
        session: Requests session with authentication headers
        full_name: Full repository name (owner/repo)
        api_url: Base API URL
        **request_kwargs: Additional request parameters

    Returns:
        True if the repo is starred, False otherwise
    """
    endpoint = f"/user/starred/{full_name}"
    try:
        make_request(
            session=session,
            method="GET",
            url=endpoint,
            api_url=api_url,
            **request_kwargs,
        )
        return True
    except QuackApiError as e:
        if hasattr(e, "status_code") and e.status_code == 404:
            return False
        raise


def fork_repo(
    session: requests.Session,
    full_name: str,
    api_url: str,
    organization: str | None = None,
    **request_kwargs: Any,
) -> GitHubRepo:
    """Fork a GitHub repository.

    Args:
        session: Requests session with authentication headers
        full_name: Full repository name (owner/repo)
        api_url: Base API URL
        organization: Optional organization name to fork to
        **request_kwargs: Additional request parameters

    Returns:
        GitHubRepo object for the new fork

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/repos/{full_name}/forks"

    params = {}
    if organization:
        params["organization"] = organization

    response = make_request(
        session=session,
        method="POST",
        url=endpoint,
        api_url=api_url,
        json=params,
        **request_kwargs,
    )

    # The API returns the new repo data
    fork_data = response.json()

    # Extract owner information
    owner_data = fork_data.get("owner", {})
    owner = GitHubUser(
        username=owner_data.get("login"),
        url=owner_data.get("html_url"),
        avatar_url=owner_data.get("avatar_url"),
    )

    # Create and return the repository object
    return GitHubRepo(
        name=fork_data.get("name"),
        full_name=fork_data.get("full_name"),
        url=fork_data.get("html_url"),
        clone_url=fork_data.get("clone_url"),
        default_branch=fork_data.get("default_branch"),
        description=fork_data.get("description"),
        fork=True,  # This is definitely a fork
        forks_count=fork_data.get("forks_count", 0),
        stargazers_count=fork_data.get("stargazers_count", 0),
        owner=owner,
    )


def check_repository_exists(
    session: requests.Session, full_name: str, api_url: str, **request_kwargs: Any
) -> bool:
    """Check if a repository exists.

    Args:
        session: Requests session with authentication headers
        full_name: Full repository name (owner/repo)
        api_url: Base API URL
        **request_kwargs: Additional request parameters

    Returns:
        True if the repository exists, False otherwise
    """
    endpoint = f"/repos/{full_name}"
    try:
        make_request(
            session=session,
            method="GET",
            url=endpoint,
            api_url=api_url,
            **request_kwargs,
        )
        return True
    except QuackApiError as e:
        if hasattr(e, "status_code") and e.status_code == 404:
            return False
        raise


def get_repository_file_content(
    session: requests.Session,
    repo: str,
    path: str,
    api_url: str,
    ref: str | None = None,
    **request_kwargs: Any,
) -> tuple[str, str]:
    """Get the content of a file from a repository.

    Args:
        session: Requests session with authentication headers
        repo: Full repository name (owner/repo)
        path: Path to the file within the repository
        api_url: Base API URL
        ref: Git reference (branch, tag, commit)
        **request_kwargs: Additional request parameters

    Returns:
        Tuple of (content, sha)

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/repos/{repo}/contents/{path}"

    params = {}
    if ref:
        params["ref"] = ref

    response = make_request(
        session=session,
        method="GET",
        url=endpoint,
        api_url=api_url,
        params=params,
        **request_kwargs,
    )

    data = response.json()
    content = data.get("content", "")

    # The content is base64 encoded, decode it
    decoded_content = base64.b64decode(content).decode("utf-8")

    return decoded_content, data.get("sha", "")


def update_repository_file(
    session: requests.Session,
    repo: str,
    path: str,
    content: str,
    message: str,
    sha: str,
    api_url: str,
    branch: str | None = None,
    **request_kwargs: Any,
) -> bool:
    """Update a file in a repository.

    Args:
        session: Requests session with authentication headers
        repo: Full repository name (owner/repo)
        path: Path to the file within the repository
        content: New file content
        message: Commit message
        sha: Current file SHA
        api_url: Base API URL
        branch: Branch to commit to
        **request_kwargs: Additional request parameters

    Returns:
        True if successful

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/repos/{repo}/contents/{path}"

    # Encode content to base64
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    data = {
        "message": message,
        "content": encoded_content,
        "sha": sha,
    }

    if branch:
        data["branch"] = branch

    make_request(
        session=session,
        method="PUT",
        url=endpoint,
        api_url=api_url,
        json=data,
        **request_kwargs,
    )
    return True
