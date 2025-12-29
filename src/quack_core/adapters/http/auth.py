# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/auth.py
# module: quack_core.adapters.http.auth
# role: adapters
# neighbors: __init__.py, app.py, service.py, models.py, config.py, dependencies.py (+1 more)
# exports: require_bearer, sign_payload
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===



"""
Authentication utilities for the HTTP adapter.
"""

import hashlib
import hmac
import json
from typing import Optional

from fastapi import HTTPException, Request

from quack_core.adapters.http.config import HttpAdapterConfig


def require_bearer(request: Request, cfg: HttpAdapterConfig) -> None:
    """
    Require Bearer token authentication.

    Args:
        request: FastAPI request object
        cfg: HTTP adapter configuration

    Raises:
        HTTPException: 401 if auth fails or token missing
    """
    if not cfg.auth_token:
        # Auth disabled for development
        return

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(401, "Authorization header required")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")

    token = auth_header[7:]  # Remove "Bearer " prefix
    if token != cfg.auth_token:
        raise HTTPException(401, "Invalid token")


def sign_payload(payload: dict, secret: str) -> str:
    """
    Sign a payload with HMAC-SHA256.

    Args:
        payload: Dictionary to sign
        secret: HMAC secret key

    Returns:
        Hex-encoded signature
    """
    body_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        secret.encode(),
        body_json.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"