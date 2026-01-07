# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/plugin.py
# module: quack_core.core.paths.plugin
# role: plugin
# neighbors: __init__.py, service.py
# exports: PathsPlugin, QuackPathsPlugin, create_plugin
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/paths/plugin.py
"""
Plugin interface for the paths module.

This module defines the plugin interface for the paths module,
allowing QuackCore to expose path resolution functionality to other modules.
"""

from pathlib import Path
from typing import Protocol

from quack_core.fs.results import DataResult, OperationResult
from quack_core.paths._internal.context import ContentContext, ProjectContext
from quack_core.paths._internal.resolver import PathResolver
from quack_core.paths._internal.utils import _normalize_path_param


class PathsPlugin(Protocol):
    """Protocol for paths plugins."""

    @property
    def name(self) -> str:
        """Name of the plugin."""
        ...

    def find_project_root(
        self,
        start_dir: str | Path | DataResult | OperationResult | None = None,
    ) -> str:
        """
        Find the project root directory.

        Args:
            start_dir: Directory to start searching from (string, Path, DataResult,
                       or OperationResult; default: current directory)

        Returns:
            Path to the project root directory as a string
        """
        ...  # pragma: no cover

    def detect_project_context(
        self,
        start_dir: str | Path | DataResult | OperationResult | None = None,
    ) -> ProjectContext:
        """
        Detect project context from a directory.

        Args:
            start_dir: Directory to start searching from (string, Path, DataResult,
                       or OperationResult; default: current directory)

        Returns:
            ProjectContext object
        """
        ...  # pragma: no cover

    def detect_content_context(
        self,
        start_dir: str | Path | DataResult | OperationResult | None = None,
        content_type: str | None = None,
    ) -> ContentContext:
        """
        Detect content context from a directory.

        Args:
            start_dir: Directory to start searching from (string, Path, DataResult,
                       or OperationResult; default: current directory)
            content_type: Type of content (optional)

        Returns:
            ContentContext object
        """
        ...  # pragma: no cover


class QuackPathsPlugin:
    """Implementation of the paths plugin protocol."""

    def __init__(self) -> None:
        """Initialize the plugin."""
        self._resolver = PathResolver()

    @property
    def name(self) -> str:
        """Name of the plugin."""
        return "paths"

    def find_project_root(
        self,
        start_dir: str | Path | DataResult | OperationResult | None = None,
    ) -> str:
        """
        Find the project root directory.

        Args:
            start_dir: Directory to start searching from (string, Path, DataResult,
                       or OperationResult; default: current directory)

        Returns:
            Path to the project root directory as a string
        """
        start = None if start_dir is None else _normalize_path_param(start_dir)
        return self._resolver._get_project_root(start)

    def detect_project_context(
        self,
        start_dir: str | Path | DataResult | OperationResult | None = None,
    ) -> ProjectContext:
        """
        Detect project context from a directory.

        Args:
            start_dir: Directory to start searching from (string, Path, DataResult,
                       or OperationResult; default: current directory)

        Returns:
            ProjectContext object
        """
        start = None if start_dir is None else _normalize_path_param(start_dir)
        return self._resolver._detect_project_context(start)

    def detect_content_context(
        self,
        start_dir: str | Path | DataResult | OperationResult | None = None,
        content_type: str | None = None,
    ) -> ContentContext:
        """
        Detect content context from a directory.

        Args:
            start_dir: Directory to start searching from (string, Path, DataResult,
                       or OperationResult; default: current directory)
            content_type: Type of content (optional)

        Returns:
            ContentContext object
        """
        start = None if start_dir is None else _normalize_path_param(start_dir)
        return self._resolver._detect_content_context(start, content_type)


def create_plugin() -> PathsPlugin:
    """Create a new instance of the paths plugin."""
    return QuackPathsPlugin()
