# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/utils/api.py
# module: quack_core.integrations.google.mail.utils.api
# role: utils
# neighbors: __init__.py
# exports: APIRequest, execute_api_request, with_exponential_backoff
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
API utilities for Google Mail integration.

This module provides wrapper functions for Gmail API calls,
with consistent error handling and logging.
"""

from collections.abc import Callable
from typing import Protocol, TypeVar, runtime_checkable

from googleapiclient.errors import HttpError

from quack_core.lib.errors import QuackApiError
from quack_core.integrations.google.mail.protocols import GmailRequest

T = TypeVar("T")  # Generic type for API response
R = TypeVar("R")  # Generic type for request results


# Add the missing APIRequest protocol that's imported in email.py
@runtime_checkable
class APIRequest(Protocol[R]):
    """Protocol for Gmail API request objects."""

    def execute(self) -> R:
        """
        Execute the request.

        Returns:
            R: The API response.
        """
        ...


def execute_api_request(
    request: GmailRequest[R], error_message: str, api_method: str
) -> R:
    """
    Execute a Gmail API request with consistent error handling.

    Args:
        request: Gmail API request object.
        error_message: Error message prefix for exceptions.
        api_method: Name of the API method being called.

    Returns:
        R: API response.

    Raises:
        QuackApiError: If the API request fails.
    """
    try:
        return request.execute()
    except HttpError as e:
        raise QuackApiError(
            f"{error_message}: {e}",
            service="Gmail",
            api_method=api_method,
            original_error=e,
        ) from e
    except Exception as e:
        raise QuackApiError(
            f"{error_message}: {e}",
            service="Gmail",
            api_method=api_method,
            original_error=e,
        ) from e


def with_exponential_backoff(
    func: Callable[..., T],
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Callable[..., T]:
    """
    Decorator for API calls with exponential backoff retry logic.

    Args:
        func: The function to wrap with retry logic.
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum delay in seconds before any retry.

    Returns:
        Callable: Wrapped function with retry logic.
    """
    import time
    from functools import wraps

    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> T:
        retry_count = 0
        delay = initial_delay

        while True:
            try:
                return func(*args, **kwargs)
            except HttpError as e:
                # Only retry on specific error codes (e.g., 429, 500, 503)
                if e.resp.status not in (429, 500, 503) or retry_count >= max_retries:
                    raise

                retry_count += 1
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            except Exception:
                # Don't retry on other exceptions
                raise

    return wrapper
