# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config/tooling/base.py
# module: quack_core.config.tooling.base
# role: module
# neighbors: __init__.py, loader.py, logger.py
# exports: QuackToolConfigModel
# git_branch: refactor/toolkitWorkflow
# git_commit: 0f9247b
# === QV-LLM:END ===

"""
Base class for QuackTool-specific config models.

This module provides the base class that all QuackTool-specific
configuration models should inherit from.
"""

from pydantic import BaseModel


class QuackToolConfigModel(BaseModel):
    """
    Base class for QuackTool-specific config models.

    Tools should subclass this with their own fields.
    This base class exists so tooling can type-check config models.
    """
    pass
