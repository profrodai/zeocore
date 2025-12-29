# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/config.py
# module: quack_core.integrations.google.mail.config
# role: module
# neighbors: __init__.py, service.py, protocols.py
# exports: GmailServiceConfig
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
Configuration for Google Mail integration.

This module extends the base Google Mail configuration with additional
settings specific to the Gmail service.
"""

from pydantic import Field

from quack_core.integrations.google.config import GoogleMailConfig


class GmailServiceConfig(GoogleMailConfig):
    """Extended configuration for Gmail service."""

    storage_path: str = Field(..., description="Path to store downloaded emails")
    oauth_scope: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/gmail.readonly"],
        description="OAuth scopes for Gmail API access",
    )
    max_retries: int = Field(5, description="Maximum number of retries for API calls")
    initial_delay: float = Field(
        1.0, description="Initial delay for exponential backoff"
    )
    max_delay: float = Field(30.0, description="Maximum delay for exponential backoff")
    include_subject: bool = Field(
        False, description="Include email subject in downloaded file"
    )
    include_sender: bool = Field(
        False, description="Include email sender in downloaded file"
    )
