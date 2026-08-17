"""
Configuration for the HTTP adapter.
"""

from pydantic import AnyHttpUrl, Field

from zeo_core.config.tooling.base import ZeoToolConfigModel


class HttpAdapterConfig(ZeoToolConfigModel):
    """Configuration for the HTTP adapter."""

    host: str = "0.0.0.0"  # noqa: S104 -- configurable default (Pydantic field, overridable at construction), not a hardcoded bind; operator chooses reachability
    port: int = 8080
    cors_origins: list[str] = Field(default_factory=list)
    auth_token: str | None = None
    hmac_secret: str | None = None
    public_base_url: AnyHttpUrl | None = None
    job_ttl_seconds: int = 3600
    max_workers: int = 4
    request_timeout_seconds: int = 900
