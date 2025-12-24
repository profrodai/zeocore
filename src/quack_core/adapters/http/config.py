# quack-core/src/quack_core/adapters/http/config.py
"""
Configuration for the HTTP adapter.
"""

from typing import List, Optional
from pydantic import BaseModel, AnyHttpUrl

from quack_core.config.tooling.base import QuackToolConfigModel


class HttpAdapterConfig(QuackToolConfigModel):
    """Configuration for the HTTP adapter."""

    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: List[str] = []
    auth_token: Optional[str] = None
    hmac_secret: Optional[str] = None
    public_base_url: Optional[AnyHttpUrl] = None
    job_ttl_seconds: int = 3600
    max_workers: int = 4
    request_timeout_seconds: int = 900