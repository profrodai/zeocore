# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/utils/api.py
# module: quack_core.integrations.github.utils.api
# role: utils
# neighbors: __init__.py
# exports: make_request
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===

"""GitHub API request utilities."""

import time
from datetime import datetime
from typing import Any

import requests
from quack_core.core.errors import (
    QuackApiError,
    QuackAuthenticationError,
    QuackQuotaExceededError,
)
from quack_core.core.logging import get_logger

logger = get_logger(__name__)


def make_request(
    session: requests.Session,
    method: str,
    url: str,
    api_url: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    **kwargs: Any,
) -> requests.Response:
    """Make an HTTP request to the GitHub API with retries.

    Args:
        session: Requests session with authentication headers
        method: HTTP method (GET, POST, PUT, DELETE)
        url: API endpoint (without base URL)
        api_url: Base API URL
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for requests
        retry_delay: Delay between retries in seconds
        params: URL parameters
        json: JSON body data
        **kwargs: Additional request parameters

    Returns:
        Response object

    Raises:
        QuackAuthenticationError: If authentication fails
        QuackQuotaExceededError: If rate limit is exceeded
        QuackApiError: For other API errors
    """
    full_url = f"{api_url}{url}"
    kwargs.setdefault("timeout", timeout)

    for attempt in range(1, max_retries + 1):
        try:
            response = session.request(
                method, full_url, params=params, json=json, **kwargs
            )

            # Check for rate limiting - Need to check before raise_for_status
            remaining = int(response.headers.get("X-RateLimit-Remaining", "1"))
            if remaining == 0 or response.status_code == 429:
                reset_time = int(response.headers.get("X-RateLimit-Reset", "0"))
                current_time = int(time.time())
                wait_time = max(1, reset_time - current_time)

                if attempt < max_retries:
                    logger.warning(
                        f"GitHub API rate limit exceeded. Waiting {wait_time} seconds before retry."
                    )
                    time.sleep(min(wait_time, 60))  # Wait at most 60 seconds
                    continue
                else:
                    # We've hit max retries, raise the quota error
                    raise QuackQuotaExceededError(
                        message=f"GitHub API rate limit exceeded. Reset at {datetime.fromtimestamp(reset_time)}",
                        service="GitHub",
                        resource=url,
                    )

            # Check for successful response
            response.raise_for_status()
            return response

        except QuackQuotaExceededError:
            # If we already raised a QuackQuotaExceededError, don't catch and re-raise it
            # This fixes the issue with nested exceptions
            raise

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code

            # Handle authentication errors
            if status_code in (401, 403):
                raise QuackAuthenticationError(
                    f"GitHub API authentication failed: {e.response.text}",
                    service="GitHub",
                    original_error=e,
                )

            # Handle rate limiting again - in case it wasn't caught above
            if status_code == 429 or (
                hasattr(e.response, "headers")
                and "X-RateLimit-Remaining" in e.response.headers
                and int(e.response.headers["X-RateLimit-Remaining"]) == 0
            ):
                reset_time = int(e.response.headers.get("X-RateLimit-Reset", "0"))
                current_time = int(time.time())
                wait_time = max(1, reset_time - current_time)

                if attempt < max_retries:
                    logger.warning(
                        f"GitHub API rate limit exceeded. Waiting {wait_time} seconds before retry."
                    )
                    time.sleep(min(wait_time, 60))  # Wait at most 60 seconds
                    continue
                else:
                    # Ensure we raise the correct error type for tests
                    raise QuackQuotaExceededError(
                        message=f"GitHub API rate limit exceeded. Reset at {datetime.fromtimestamp(reset_time)}",
                        service="GitHub",
                        resource=url,
                        original_error=e,
                    )

            # For server errors, retry
            if status_code >= 500 and attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"GitHub API server error (status {status_code}). "
                    f"Retrying in {wait_time:.1f} seconds..."
                )
                time.sleep(wait_time)
                continue

            # For other errors, raise with appropriate context
            error_message = str(e)
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_message = error_data["message"]
            except (ValueError, KeyError, AttributeError):
                pass

            raise QuackApiError(
                f"GitHub API error: {error_message}",
                service="GitHub",
                status_code=status_code,
                api_method=url,
                original_error=e,
            )

        except requests.exceptions.ConnectionError as e:
            # Retry connection errors
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"GitHub API connection error. Retrying in {wait_time:.1f} seconds..."
                )
                time.sleep(wait_time)
                continue

            raise QuackApiError(
                f"GitHub API connection error: {str(e)}",
                service="GitHub",
                api_method=url,
                original_error=e,
            )

        except requests.exceptions.Timeout as e:
            # Retry timeouts
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"GitHub API timeout. Retrying in {wait_time:.1f} seconds..."
                )
                time.sleep(wait_time)
                continue

            raise QuackApiError(
                f"GitHub API timeout: {str(e)}",
                service="GitHub",
                api_method=url,
                original_error=e,
            )

        except Exception as e:
            # For other unexpected errors, don't try to catch our own exceptions
            if isinstance(e, QuackQuotaExceededError) or isinstance(
                e, QuackAuthenticationError
            ):
                raise

            # Unexpected errors
            raise QuackApiError(
                f"Unexpected error in GitHub API request: {str(e)}",
                service="GitHub",
                api_method=url,
                original_error=e,
            )
