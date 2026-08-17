"""
Base class for ZeoTool-specific config models.

This module provides the base class that all ZeoTool-specific
configuration models should inherit from.
"""

from pydantic import BaseModel


class ZeoToolConfigModel(BaseModel):
    """
    Base class for ZeoTool-specific config models.

    Tools should subclass this with their own fields.
    This base class exists so tooling can type-check config models.
    """

    pass
