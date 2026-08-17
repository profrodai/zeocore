"""
Pandoc integration for zeo_core.

This package provides an integration for document conversion using Pandoc,
including HTML to Markdown and Markdown to DOCX conversion.
"""

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.pandoc.config import PandocConfig, PandocConfigProvider
from zeo_core.integrations.pandoc.converter import DocumentConverter
from zeo_core.integrations.pandoc.models import (
    ConversionMetrics,
    ConversionTask,
    FileInfo,
)
from zeo_core.integrations.pandoc.service import PandocIntegration

__all__ = [
    # Main integration class
    "PandocIntegration",
    # Configuration
    "PandocConfig",
    "PandocConfigProvider",
    # Core converter
    "DocumentConverter",
    # Models
    "ConversionMetrics",
    "ConversionTask",
    "FileInfo",
    # Factory function for integration discovery
    "create_integration",
]


def create_integration() -> IntegrationProtocol:
    """
    Create and return a Pandoc integration instance.

    This function is used as an entry point for automatic integration discovery.

    Returns:
        IntegrationProtocol: Configured Pandoc integration
    """
    return PandocIntegration()
