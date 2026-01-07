# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/plugin.py
# module: quack_core.core.fs.plugin
# role: plugin
# neighbors: __init__.py, protocols.py, results.py
# exports: FSPlugin, QuackFSPlugin, create_plugin
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/plugin.py
"""
Plugin interface for the filesystem module.

This module defines the plugin interface for the filesystem module,
allowing QuackCore to expose filesystem functionality to other modules.
"""

from pathlib import Path
from typing import Protocol, TypeVar

from quack_core.fs.results import (
    DataResult,
    OperationResult,
    ReadResult,
    WriteResult,
)
from quack_core.fs.service import FileSystemService

T = TypeVar("T")


class FSPlugin(Protocol):
    """Protocol for filesystem plugins."""

    @property
    def name(self) -> str:
        """Name of the plugin."""
        ...

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> ReadResult[str]:
        """
        Read text from a file.

        Args:
            path: Path to the file
            encoding: Text encoding

        Returns:
            ReadResult with the file content as text
        """
        ...

    def write_text(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
        atomic: bool = True,
    ) -> WriteResult:
        """
        Write text to a file.

        Args:
            path: Path to the file
            content: Content to write
            encoding: Text encoding
            atomic: Whether to use atomic writing

        Returns:
            WriteResult with operation status
        """
        ...

    def read_yaml(self, path: str | Path) -> DataResult[dict]:
        """
        Read YAML file and parse its contents.

        Args:
            path: Path to YAML file

        Returns:
            DataResult with parsed YAML data
        """
        ...

    def write_yaml(
        self,
        path: str | Path,
        data: dict,
        atomic: bool = True,
    ) -> WriteResult:
        """
        Write data to a YAML file.

        Args:
            path: Path to YAML file
            data: Data to write
            atomic: Whether to use atomic writing

        Returns:
            WriteResult with operation status
        """
        ...

    def create_directory(
        self, path: str | Path, exist_ok: bool = True
    ) -> OperationResult:
        """
        Create a directory.

        Args:
            path: Path to create
            exist_ok: Whether to ignore if the directory already exists

        Returns:
            OperationResult with operation status
        """
        ...


class QuackFSPlugin:
    """Implementation of the filesystem plugin protocol."""

    def __init__(self) -> None:
        """Initialize the plugin."""
        self._service = FileSystemService()

    @property
    def name(self) -> str:
        """Name of the plugin."""
        return "fs"

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> ReadResult[str]:
        """
        Read text from a file.

        Args:
            path: Path to the file
            encoding: Text encoding

        Returns:
            ReadResult with the file content as text
        """
        return self._service.read_text(path, encoding)

    def write_text(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
        atomic: bool = True,
    ) -> WriteResult:
        """
        Write text to a file.

        Args:
            path: Path to the file
            content: Content to write
            encoding: Text encoding
            atomic: Whether to use atomic writing

        Returns:
            WriteResult with operation status
        """
        return self._service.write_text(path, content, encoding, atomic)

    def read_yaml(self, path: str | Path) -> DataResult[dict]:
        """
        Read YAML file and parse its contents.

        Args:
            path: Path to YAML file

        Returns:
            DataResult with parsed YAML data
        """
        return self._service.read_yaml(path)

    def write_yaml(
        self,
        path: str | Path,
        data: dict,
        atomic: bool = True,
    ) -> WriteResult:
        """
        Write data to a YAML file.

        Args:
            path: Path to YAML file
            data: Data to write
            atomic: Whether to use atomic writing

        Returns:
            WriteResult with operation status
        """
        return self._service.write_yaml(path, data, atomic)

    def create_directory(
        self, path: str | Path, exist_ok: bool = True
    ) -> OperationResult:
        """
        Create a directory.

        Args:
            path: Path to create
            exist_ok: Whether to ignore if the directory already exists

        Returns:
            OperationResult with operation status
        """
        return self._service.create_directory(path, exist_ok)


def create_plugin() -> FSPlugin:
    """Create a new instance of the filesystem plugin."""
    return QuackFSPlugin()
