# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/util.py
# module: quack_core.adapters.http.util
# role: adapters
# neighbors: __init__.py, app.py, service.py, models.py, config.py, auth.py (+1 more)
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===



"""
Utility functions for the HTTP adapter.
"""

from typing import Any

import httpx
from quack_core.core.logging import get_logger

logger = get_logger(__name__)


async def post_callback(
        url: str,
        body: dict[str, Any],
        signature_header: str | None = None,
        timeout: int = 10,
) -> None:
    """
    POST a callback with optional HMAC signature.

    Raises on HTTP errors or connection failures - caller should handle.

    Args:
        url: Callback URL
        body: JSON body to post
        signature_header: Optional signature header value
        timeout: Request timeout in seconds

    Raises:
        httpx.HTTPError: On HTTP errors or connection failures
    """
    headers = {"Content-Type": "application/json"}
    if signature_header:
        headers["X-Quack-Signature"] = signature_header

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        logger.info(f"Callback posted successfully to {url}")
