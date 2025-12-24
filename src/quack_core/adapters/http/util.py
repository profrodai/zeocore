# quack-core/src/quack_core/adapters/http/util.py
"""
Utility functions for the HTTP adapter.
"""

import hashlib
import json
import uuid
from typing import Dict, Any, Optional

import httpx

from quack_core.logging import get_logger

logger = get_logger(__name__)


def new_id() -> str:
    """Generate a new UUID4 job ID."""
    return str(uuid.uuid4())


def stable_hash(payload: dict) -> str:
    """
    Generate a stable hash for a payload.

    Args:
        payload: Dictionary to hash

    Returns:
        SHA256 hex digest
    """
    json_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


async def post_callback(
        url: str,
        body: Dict[str, Any],
        signature_header: Optional[str] = None,
        timeout: int = 10
) -> None:
    """
    POST a callback with optional HMAC signature.

    Args:
        url: Callback URL
        body: JSON body to post
        signature_header: Optional signature header value
        timeout: Request timeout in seconds
    """
    headers = {"Content-Type": "application/json"}
    if signature_header:
        headers["X-Quack-Signature"] = signature_header

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            logger.info(f"Callback posted successfully to {url}")
    except Exception as e:
        logger.error(f"Failed to post callback to {url}: {e}")