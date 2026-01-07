# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/_internal/context.py
# module: quack_core.core.paths._internal.context
# role: module
# neighbors: __init__.py, utils.py, resolver.py
# exports: ProjectDirectory, ProjectContext, ContentContext, PathInfo
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/paths/_internal/context.py
"""
Project context models for path resolution.

This module provides data models for representing project structure context,
which is used for resolving paths in a project.
"""

from pydantic import BaseModel, ConfigDict, Field


# Helper function to compute the relative path (if applicable)
def _compute_relative_path(path: str, root: str) -> str | None:
    """
    Compute the relative path of `path` relative to `root`, if possible.

    Args:
        path: The absolute path as a string.
        root: The project root directory as a string.

    Returns:
        The relative path as a string if `path` starts with `root`, otherwise None.
    """
    # Assumes paths are already normalized using quack_core.fs utilities.
    if path.startswith(root):
        rel = path[len(root) :]
        return rel.lstrip("/\\")
    return None


class ProjectDirectory(BaseModel):
    """
    Represents a project directory structure.

    This model contains information about a specific directory in a project,
    such as a source code directory or an output directory.
    """

    name: str = Field(description="Name of the directory")
    path: str = Field(description="Absolute path to the directory")
    rel_path: str | None = Field(
        default=None, description="Relative path from the project root"
    )
    is_source: bool = Field(
        default=False, description="Whether this is a source code directory"
    )
    is_output: bool = Field(
        default=False, description="Whether this is an output directory"
    )
    is_data: bool = Field(default=False, description="Whether this is a data directory")
    is_config: bool = Field(
        default=False, description="Whether this is a configuration directory"
    )
    is_test: bool = Field(default=False, description="Whether this is a test directory")
    is_asset: bool = Field(
        default=False, description="Whether this is an asset directory"
    )
    is_temp: bool = Field(
        default=False, description="Whether this is a temporary directory"
    )

    def __str__(self) -> str:
        """String representation of the directory."""
        return self.path


class ProjectContext(BaseModel):
    """
    Represents the context of a project.

    This model contains information about the project structure,
    such as the root directory, source code directories, and output directories.
    """

    root_dir: str = Field(
        description="Root directory of the project",
    )

    directories: dict[str, ProjectDirectory] = Field(
        default_factory=dict,
        description="Dictionary of project directories by name",
    )

    config_file: str | None = Field(
        default=None,
        description="Path to the project configuration file",
    )

    name: str | None = Field(
        default=None,
        description="Name of the project",
    )

    def __str__(self) -> str:
        """String representation of the project context."""
        return f"ProjectContext(root={self.root_dir}, dirs={len(self.directories)})"

    def _get_source_dir(self) -> str | None:
        """
        Get the primary source directory.

        Returns:
            The path to the source directory as a string, or None if not found.
        """
        for dir_info in self.directories.values():
            if dir_info.is_source:
                return dir_info.path
        return None

    def _get_output_dir(self) -> str | None:
        """
        Get the primary output directory.

        Returns:
            The path to the output directory as a string, or None if not found.
        """
        for dir_info in self.directories.values():
            if dir_info.is_output:
                return dir_info.path
        return None

    def _get_data_dir(self) -> str | None:
        """
        Get the primary data directory.

        Returns:
            The path to the data directory as a string, or None if not found.
        """
        for dir_info in self.directories.values():
            if dir_info.is_data:
                return dir_info.path
        return None

    def _get_config_dir(self) -> str | None:
        """
        Get the primary configuration directory.

        Returns:
            The path to the configuration directory as a string, or None if not found.
        """
        for dir_info in self.directories.values():
            if dir_info.is_config:
                return dir_info.path
        return None

    def _get_directory(self, name: str) -> str | None:
        """
        Get a directory by name.

        Args:
            name: Name of the directory.

        Returns:
            The directory path as a string, or None if not found.
        """
        dir_info = self.directories.get(name)
        return dir_info.path if dir_info else None

    def _add_directory(
        self,
        name: str,
        path: str,
        is_source: bool = False,
        is_output: bool = False,
        is_data: bool = False,
        is_config: bool = False,
        is_test: bool = False,
        is_asset: bool = False,
        is_temp: bool = False,
    ) -> None:
        """
        Add a directory to the project context.

        Args:
            name: Name of the directory.
            path: Absolute path to the directory as a string.
            is_source: Whether this is a source code directory.
            is_output: Whether this is an output directory.
            is_data: Whether this is a data directory.
            is_config: Whether this is a configuration directory.
            is_test: Whether this is a test directory.
            is_asset: Whether this is an asset directory.
            is_temp: Whether this is a temporary directory.
        """
        rel_path = _compute_relative_path(path, self.root_dir)
        self.directories[name] = ProjectDirectory(
            name=name,
            path=path,
            rel_path=rel_path,
            is_source=is_source,
            is_output=is_output,
            is_data=is_data,
            is_config=is_config,
            is_test=is_test,
            is_asset=is_asset,
            is_temp=is_temp,
        )


class ContentContext(ProjectContext):
    """
    Represents the context of a content creation project.

    Extends ProjectContext with content creation–specific information.
    """

    content_type: str | None = Field(
        default=None,
        description="Type of content (e.g., 'tutorial', 'video', 'image')",
    )

    content_name: str | None = Field(
        default=None,
        description="Name of the content item",
    )

    content_dir: str | None = Field(
        default=None,
        description="Path to the content directory",
    )

    def _get_assets_dir(self) -> str | None:
        """
        Get the assets directory.

        Returns:
            The path to the assets directory as a string, or None if not found.
        """
        for dir_info in self.directories.values():
            if dir_info.is_asset:
                return dir_info.path
        return None

    def _get_temp_dir(self) -> str | None:
        """
        Get the temporary directory.

        Returns:
            The path to the temporary directory as a string, or None if not found.
        """
        for dir_info in self.directories.values():
            if dir_info.is_temp:
                return dir_info.path
        return None


# Redefine PathInfo to work with strings
class PathInfo(BaseModel):
    """Information about a normalized path."""

    success: bool = Field(..., description="Whether normalization succeeded")
    path: str = Field(..., description="Normalized path as a string")
    error: Exception | None = Field(
        default=None,
        description="Error encountered during normalization",
    )

    # allow Exception objects in the schema
    model_config = ConfigDict(arbitrary_types_allowed=True)
