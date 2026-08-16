# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/operations/issues.py
# === QV-LLM:END ===

"""GitHub issues _ops."""

from typing import Any, Literal

import requests
from quack_core.integrations.github.utils.api import make_request


def create_issue(
    session: requests.Session,
    repo: str,
    title: str,
    api_url: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    **request_kwargs: Any,  # noqa: ANN401 -- passthrough to requests.Session.request via make_request; kwargs are genuinely heterogeneous
) -> dict[str, Any]:
    """Create an issue in a repository.

    Args:
        session: Requests session with authentication headers
        repo: Full repository name (owner/repo)
        title: Issue title
        api_url: Base API URL
        body: Issue body
        labels: List of labels to apply
        assignees: List of users to assign
        **request_kwargs: Additional request parameters

    Returns:
        Issue data dictionary

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/repos/{repo}/issues"

    data: dict[str, Any] = {
        "title": title,
    }

    if body:
        data["body"] = body

    if labels:
        data["labels"] = labels

    if assignees:
        data["assignees"] = assignees

    response = make_request(
        session=session,
        method="POST",
        url=endpoint,
        api_url=api_url,
        json=data,
        **request_kwargs,
    )

    result: dict[str, Any] = response.json()
    return result


def list_issues(
    session: requests.Session,
    repo: str,
    api_url: str,
    state: Literal["open", "closed", "all"] = "open",
    labels: str | None = None,
    sort: Literal["created", "updated", "comments"] = "created",
    direction: Literal["asc", "desc"] = "desc",
    **request_kwargs: Any,  # noqa: ANN401 -- passthrough to requests.Session.request via make_request; kwargs are genuinely heterogeneous
) -> list[dict[str, Any]]:
    """List issues in a repository.

    Args:
        session: Requests session with authentication headers
        repo: Full repository name (owner/repo)
        api_url: Base API URL
        state: Issue state (open, closed, all)
        labels: Comma-separated list of label names
        sort: What to sort results by
        direction: Direction to sort
        **request_kwargs: Additional request parameters

    Returns:
        List of issue data dictionaries

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/repos/{repo}/issues"

    params: dict[str, Any] = {"state": state, "sort": sort, "direction": direction}

    if labels:
        params["labels"] = labels

    response = make_request(
        session=session,
        method="GET",
        url=endpoint,
        api_url=api_url,
        params=params,
        **request_kwargs,
    )

    result: list[dict[str, Any]] = response.json()
    return result


def get_issue(
    session: requests.Session,
    repo: str,
    issue_number: int,
    api_url: str,
    **request_kwargs: Any,  # noqa: ANN401 -- passthrough to requests.Session.request via make_request; kwargs are genuinely heterogeneous
) -> dict[str, Any]:
    """Get a specific issue in a repository.

    Args:
        session: Requests session with authentication headers
        repo: Full repository name (owner/repo)
        issue_number: Issue number
        api_url: Base API URL
        **request_kwargs: Additional request parameters

    Returns:
        Issue data dictionary

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/repos/{repo}/issues/{issue_number}"

    response = make_request(
        session=session, method="GET", url=endpoint, api_url=api_url, **request_kwargs
    )

    result: dict[str, Any] = response.json()
    return result


def add_issue_comment(
    session: requests.Session,
    repo: str,
    issue_number: int,
    body: str,
    api_url: str,
    **request_kwargs: Any,  # noqa: ANN401 -- passthrough to requests.Session.request via make_request; kwargs are genuinely heterogeneous
) -> dict[str, Any]:
    """Add a comment to an issue.

    Args:
        session: Requests session with authentication headers
        repo: Full repository name (owner/repo)
        issue_number: Issue number
        body: Comment body
        api_url: Base API URL
        **request_kwargs: Additional request parameters

    Returns:
        Comment data dictionary

    Raises:
        QuackApiError: If the API request fails
    """
    endpoint = f"/repos/{repo}/issues/{issue_number}/comments"

    data = {"body": body}

    response = make_request(
        session=session,
        method="POST",
        url=endpoint,
        api_url=api_url,
        json=data,
        **request_kwargs,
    )

    result: dict[str, Any] = response.json()
    return result
