# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/toolkit/protocol.py
# module: quack_core.toolkit.protocol
# role: module
# neighbors: __init__.py, base.py
# exports: QuackToolPluginProtocol
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Protocol definition for QuackTool plugins.

This module defines the interface that all QuackTool plugins must implement
to be discoverable and usable within the QuackCore ecosystem.
"""


from logging import Logger
from typing import Any, Protocol

from quack_core.integrations.core import IntegrationResult
from quack_core.plugins.protocols import QuackPluginMetadata


class QuackToolPluginProtocol(Protocol):
    """
    Protocol defining the required interface for QuackTool plugins.

    All QuackTool plugins must implement this interface to be discoverable
    and usable within the QuackCore ecosystem.
    """

    @property
    def name(self) -> str:
        """
        Returns the name of the tool.

        Returns:
            str: The tool's name identifier.
        """
        ...

    @property
    def version(self) -> str:
        """
        Returns the version of the tool.

        Returns:
            str: Semantic version of the tool.
        """
        ...

    @property
    def logger(self) -> Logger:
        """
        Returns the logger instance for the tool.

        Returns:
            Logger: Logger instance for the tool.
        """
        ...

    def get_metadata(self) -> QuackPluginMetadata:
        """
        Returns metadata about the plugin.

        Returns:
            QuackPluginMetadata: Structured metadata for the plugin.
        """
        ...

    def initialize(self) -> IntegrationResult:
        """
        Initialize the plugin and its dependencies.

        Returns:
            IntegrationResult: Result of the initialization process.
        """
        ...

    def is_available(self) -> bool:
        """
        Check if the plugin is available and ready to use.

        Returns:
            bool: True if the plugin is available, False otherwise.
        """
        ...

    def process_file(
            self,
            file_path: str,
            output_path: str | None = None,
            options: dict[str, Any] | None = None
    ) -> IntegrationResult:
        """
        Process a file with the plugin.

        Args:
            file_path: Path to the file to process
            output_path: Optional path where to write output (if None, uses default)
            options: Optional dictionary of processing options

        Returns:
            IntegrationResult: Result of the processing operation
        """
        ...
