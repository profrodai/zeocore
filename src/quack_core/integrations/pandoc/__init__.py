# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/pandoc/__init__.py
# module: quack_core.integrations.pandoc.__init__
# role: module
# neighbors: service.py, models.py, protocols.py, config.py, converter.py
# exports: PandocIntegration, PandocConfig, PandocConfigProvider, DocumentConverter, ConversionMetrics, ConversionTask, FileInfo, create_integration
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

"""
Pandoc integration for quack_core.

This package provides an integration for document conversion using Pandoc,
including HTML to Markdown and Markdown to DOCX conversion.
"""

from quack_core.integrations.core.protocols import IntegrationProtocol
from quack_core.integrations.pandoc.config import PandocConfig, PandocConfigProvider
from quack_core.integrations.pandoc.converter import DocumentConverter
from quack_core.integrations.pandoc.models import (
    ConversionMetrics,
    ConversionTask,
    FileInfo,
)
from quack_core.integrations.pandoc.service import PandocIntegration

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
