# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/models.py
# module: quack_core.core.paths.models
# role: models
# neighbors: __init__.py, service.py, plugin.py
# exports: ProjectDirectory, ProjectContext, ContentContext, PathInfo
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Project context models for path resolution.

This module provides data models for representing project structure context.
These are public models used in API results.
"""

from pydantic import BaseModel, ConfigDict, Field


def _compute_relative_path(path: str, root: str) -> str | None:
    """
    Compute the relative path of `path` relative to `root`, if possible.
    """
    try:
        # Ensure strict string comparison
        if path.startswith(root):
            rel = path[len(root) :]
            return rel.lstrip("/\\")
    except Exception:
        pass
    return None


class ProjectDirectory(BaseModel):
    """
    Represents a project directory structure.
    """

    name: str = Field(description="Name of the directory")
    path: str = Field(description="Absolute path to the directory")
    rel_path: str | None = Field(
        default=None, description="Relative path from the project root"
    )
    is_source: bool = Field(default=False, description="Source code directory")
    is_output: bool = Field(default=False, description="Output directory")
    is_data: bool = Field(default=False, description="Data directory")
    is_config: bool = Field(default=False, description="Configuration directory")
    is_test: bool = Field(default=False, description="Test directory")
    is_asset: bool = Field(default=False, description="Asset directory")
    is_temp: bool = Field(default=False, description="Temporary directory")

    def __str__(self) -> str:
        return self.path


class ProjectContext(BaseModel):
    """
    Represents the context of a project.
    """

    root_dir: str = Field(description="Root directory of the project")

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
        return f"ProjectContext(root={self.root_dir}, dirs={len(self.directories)})"

    def _get_source_dir(self) -> str | None:
        for dir_info in self.directories.values():
            if dir_info.is_source:
                return dir_info.path
        return None

    def _get_output_dir(self) -> str | None:
        for dir_info in self.directories.values():
            if dir_info.is_output:
                return dir_info.path
        return None

    def _get_directory(self, name: str) -> str | None:
        dir_info = self.directories.get(name)
        return dir_info.path if dir_info else None

    def _add_directory(
        self,
        name: str,
        path: str,
        **flags: bool,
    ) -> None:
        """Internal helper to add directory with flags."""
        rel_path = _compute_relative_path(path, self.root_dir)
        self.directories[name] = ProjectDirectory(
            name=name,
            path=path,
            rel_path=rel_path,
            **flags,
        )


class ContentContext(ProjectContext):
    """
    Represents the context of a content creation project.
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


class PathInfo(BaseModel):
    """Information about a normalized path."""

    success: bool = Field(..., description="Whether normalization succeeded")
    path: str = Field(..., description="Normalized path as a string")
    error: Exception | None = Field(
        default=None,
        description="Error encountered during normalization",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)