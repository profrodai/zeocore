"""
Jupytext integration for zeo_core.

This package provides an integration for paired notebook/script conversion
using jupytext -- converting between Jupyter notebooks (``.ipynb``) and
paired plain-text formats (percent-format ``.py``, markdown, etc.) and back.

This is the operation the org's own quackslides app (ducktyper-ai/quackslides)
hand-rolls today via a direct ``jupytext``/``nbformat`` dependency
(``quackslides/notebook/converter.py``): ``jupytext.reads(text,
fmt="py:percent")`` to parse percent-format exercise files, then
``jupytext.writes(notebook, fmt="ipynb")`` to serialize the result. This
integration wraps the same two calls with zeocore's usual integration
conventions (config, error handling, entry-point registration) and adds the
inverse direction (notebook -> script) for a complete, reusable wrapper.
"""

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.jupytext.config import JupytextConfig, JupytextConfigProvider
from zeo_core.integrations.jupytext.converter import NotebookConverter
from zeo_core.integrations.jupytext.models import (
    ConversionDetails,
    ConversionTask,
    NotebookInfo,
)
from zeo_core.integrations.jupytext.service import JupytextIntegration

__all__ = [
    # Main integration class
    "JupytextIntegration",
    # Configuration
    "JupytextConfig",
    "JupytextConfigProvider",
    # Core converter
    "NotebookConverter",
    # Models
    "ConversionDetails",
    "ConversionTask",
    "NotebookInfo",
    # Factory function for integration discovery
    "create_integration",
]


def create_integration() -> IntegrationProtocol:
    """
    Create and return a jupytext integration instance.

    This function is used as an entry point for automatic integration discovery.

    Returns:
        IntegrationProtocol: Configured jupytext integration
    """
    return JupytextIntegration()
