# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/operations/users.py
# module: quack_core.integrations.github.operations.users
# role: operations
# neighbors: __init__.py, issues.py, pull_requests.py, repositories.py
# exports: get_user
# git_branch: refactor/newHeaders
# git_commit: bd13631
# === QV-LLM:END ===

"""GitHub user _operations."""

from typing import Any

import requests

from quack_core.integrations.github.models import GitHubUser
from quack_core.integrations.github.utils.api import make_request


def get_user(
    session: requests.Session,
    api_url: str,
    username: str | None = None,
    **request_kwargs: Any,
) -> GitHubUser:
    """Get information about a GitHub user.

    Args:
        session: Requests session with authentication headers
        api_url: Base API URL
        username: GitHub username. If None, gets the authenticated user.
        **request_kwargs: Additional request parameters

    Returns:
        GitHubUser object

    Raises:
        QuackApiError: If the API request fails
        QuackAuthenticationError: If authentication fails
    """
    if username is None:
        # Get authenticated user
        endpoint = "/user"
    else:
        endpoint = f"/users/{username}"

    response = make_request(
        session=session, method="GET", url=endpoint, api_url=api_url, **request_kwargs
    )

    user_data = response.json()

    return GitHubUser(
        username=user_data.get("login"),
        url=user_data.get("html_url"),
        name=user_data.get("name"),
        email=user_data.get("email"),
        avatar_url=user_data.get("avatar_url"),
    )
