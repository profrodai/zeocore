# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/config.py
# module: quack_core.integrations.config
# role: module
# neighbors: __init__.py, boot.py, loader.py
# exports: IntegrationsConfig
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Core configuration models for integrations.

This module provides generic configuration structures for the integrations system.
It remains agnostic of specific integration implementations to strictly verify
core purity doctrine.
"""

from typing import Any

from pydantic import BaseModel, Field


class IntegrationsConfig(BaseModel):
    """
    Global configuration for the integrations subsystem.
    """

    enabled: list[str] = Field(
        default_factory=list,
        description="List of integration IDs that should be loaded at runtime.",
    )

    # Use a generic mapping for specific integration configs to avoid hard dependencies
    settings: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Configuration settings keyed by integration ID (e.g., 'github', 'google.mail').",
    )

    strict_loading: bool = Field(
        default=True,
        description="If True, the boot process fails if an enabled integration cannot be loaded.",
    )
