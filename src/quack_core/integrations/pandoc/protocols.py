# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/pandoc/protocols.py
# module: quack_core.integrations.pandoc.protocols
# role: protocols
# neighbors: __init__.py, service.py, models.py, config.py, converter.py
# exports: DocumentConverterProtocol, BatchConverterProtocol, PandocConversionProtocol
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

"""
Protocol definitions for Pandoc integration.

This module defines protocol classes for document conversion services,
ensuring proper typing throughout the codebase. In this refactored version,
all file paths are represented as strings rather than pathlib.Path objects.
File resolution and normalization are delegated to quack_core.core.fs.
"""

from collections.abc import Sequence
from typing import Protocol, TypeVar, runtime_checkable

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.models import ConversionTask

# Generic type variables for flexible return types
T = TypeVar("T")
R = TypeVar("R")


@runtime_checkable
class DocumentConverterProtocol(Protocol):
    """
    Protocol for document converter implementations.
    All file path parameters and return types are strings.
    """

    def convert_file(
        self, input_path: str, output_path: str, output_format: str
    ) -> IntegrationResult[str]:
        """
        Convert a file from one format to another.

        Args:
            input_path: The absolute path to the input file (as a string).
            output_path: The absolute path to the output file (as a string).
            output_format: The target output format.

        Returns:
            IntegrationResult[str]: Result of the conversion, with the output file path.
        """
        ...

    def validate_conversion(self, output_path: str, input_path: str) -> bool:
        """
        Validate the converted document.

        Args:
            output_path: The absolute path to the output file (as a string).
            input_path: The absolute path to the input file (as a string).

        Returns:
            bool: True if validation passed, False otherwise.
        """
        ...


@runtime_checkable
class BatchConverterProtocol(Protocol):
    """
    Protocol for batch document conversion.
    File path parameters and results are represented as strings.
    """

    def convert_batch(
        self, tasks: Sequence[ConversionTask], output_dir: str | None = None
    ) -> IntegrationResult[list[str]]:
        """
        Convert a batch of files.

        Args:
            tasks: A list of conversion tasks.
            output_dir: A directory (absolute path as a string) where to save converted files
                        or None to use each task's output configuration.

        Returns:
            IntegrationResult[list[str]]: Result of the batch conversion, with a list of output file paths.
        """
        ...


@runtime_checkable
class PandocConversionProtocol(Protocol):
    """
    Protocol for the main pandoc conversion _ops.
    File path parameters and return types are represented as strings.
    """

    def html_to_markdown(
        self, html_path: str, output_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Convert HTML to Markdown.

        Args:
            html_path: The absolute path to the HTML file (as a string).
            output_path: Optional absolute path to save the Markdown file (as a string).

        Returns:
            IntegrationResult[str]: Result of the conversion with the output file path.
        """
        ...

    def markdown_to_docx(
        self, markdown_path: str, output_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Convert Markdown to DOCX.

        Args:
            markdown_path: The absolute path to the Markdown file (as a string).
            output_path: Optional absolute path to save the DOCX file (as a string).

        Returns:
            IntegrationResult[str]: Result of the conversion with the output file path.
        """
        ...

    def convert_directory(
        self,
        input_dir: str,
        output_format: str,
        output_dir: str | None = None,
        file_pattern: str | None = None,
        recursive: bool = False,
    ) -> IntegrationResult[list[str]]:
        """
        Convert all files in a directory.

        Args:
            input_dir: The absolute path to the directory containing files to convert (as a string).
            output_format: The target output format (e.g., "markdown" or "docx").
            output_dir: Optional absolute path to the directory in which to save converted files (as a string).
            file_pattern: Optional glob pattern to match specific files.
            recursive: Whether to search subdirectories.

        Returns:
            IntegrationResult[list[str]]: Result of the conversion with a list of output file paths.
        """
        ...
