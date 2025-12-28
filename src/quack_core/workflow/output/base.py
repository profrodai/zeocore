# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/workflow/output/base.py
# module: quack_core.workflow.output.base
# role: module
# neighbors: __init__.py, writers.py
# exports: OutputWriter
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
Abstract base class for output writers.

This module defines the common interface for all output writers in quack_core.
Output writers are responsible for serializing and persisting data to files in
various formats.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


class OutputWriter(ABC):
    """
    Abstract base class for output writers.

    Writers define how to serialize and save output data in different formats.
    Each writer implements a specific serialization format and handles any
    format-specific validation and configuration.
    """

    @abstractmethod
    def write_output(self, data: Any, output_path: str | Path) -> str:
        """
        Write the given data to the specified output path.

        Args:
            data: The data to write
            output_path: Path where the output should be saved

        Returns:
            The final output path (may be modified to add extensions)

        Raises:
            ValueError: If the data is invalid for this writer
            RuntimeError: If the write operation fails
        """
        pass

    @abstractmethod
    def get_extension(self) -> str:
        """
        Get the file extension associated with this writer.

        Example: '.json', '.yaml', '.csv', etc.

        Returns:
            File extension with leading dot
        """
        pass

    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """
        Validate whether the provided data is suitable for writing.

        Args:
            data: The data to validate

        Returns:
            True if valid

        Raises:
            ValueError: If the data is invalid for this writer
        """
        pass
