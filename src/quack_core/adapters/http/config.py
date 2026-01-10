# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/config.py
# module: quack_core.adapters.http.config
# role: adapters
# neighbors: __init__.py, app.py, service.py, models.py, auth.py, dependencies.py (+1 more)
# exports: HttpAdapterConfig
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===


"""
Configuration for the HTTP adapter.
"""


from pydantic import AnyHttpUrl, Field
from quack_core.config.tooling.base import QuackToolConfigModel


class HttpAdapterConfig(QuackToolConfigModel):
    """Configuration for the HTTP adapter."""

    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: list[str] = Field(default_factory=list)
    auth_token: str | None = None
    hmac_secret: str | None = None
    public_base_url: AnyHttpUrl | None = None
    job_ttl_seconds: int = 3600
    max_workers: int = 4
    request_timeout_seconds: int = 900
