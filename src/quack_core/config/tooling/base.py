# quack-core/src/quack_core/config/tooling/base.py
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
