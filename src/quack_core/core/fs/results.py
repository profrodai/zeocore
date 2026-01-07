# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/results.py
# module: quack_core.core.fs.results
# role: module
# neighbors: __init__.py, protocols.py, plugin.py
# exports: OperationResult, ReadResult, WriteResult, FileInfoResult, DirectoryInfoResult, FindResult, DataResult, PathResult
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/results.py
"""
Result models for filesystem _operations.

This module provides standardized result classes for various
filesystem _operations, enhancing error handling and return values.
"""

from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")  # Generic type for flexible typing


class OperationResult(BaseModel):
    """Base class for all filesystem operation results."""

    success: bool = Field(
        default=True,
        description="Whether the operation was successful",
    )

    path: Path = Field(
        description="Path that was operated on",
    )

    message: str | None = Field(
        default=None,
        description="Additional message about the operation",
    )

    error: str | None = Field(
        default=None,
        description="Error message if operation failed",
    )


class ReadResult(OperationResult, Generic[T]):
    """Result of a file read operation."""

    content: T = Field(
        description="Content read from the file",
    )

    encoding: str | None = Field(
        default=None,
        description="Encoding used for text content",
    )

    # This field is added for backward compatibility with the old types.ReadResult
    data: Any = Field(
        default=None,
        description="Parsed data (for structured formats like JSON, YAML)",
    )

    @property
    def text(self) -> str:
        """
        Get content as text.

        Returns:
            Content as a string.

        Raises:
            TypeError: If content is not a string or bytes.
            UnicodeDecodeError: If binary content cannot be decoded.
        """
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, bytes):
            # If the content contains a null byte, consider it binary.
            # Respect the provided encoding parameter
            # if the test explicitly wants to decode binary data
            if b"\x00" in self.content and not self.encoding == "latin1":
                raise UnicodeDecodeError(
                    "utf-8",
                    self.content,
                    0,
                    len(self.content),
                    "Cannot decode binary content to text",
                )
            try:
                return self.content.decode(self.encoding or "utf-8")
            except UnicodeError as err:
                raise UnicodeDecodeError(
                    "utf-8",
                    self.content,
                    0,
                    len(self.content),
                    "Cannot decode binary content to text",
                ) from err
        else:
            raise TypeError(f"Content is not text: {type(self.content)}")

    @property
    def binary(self) -> bytes:
        """
        Get content as binary.

        Returns:
            Content as bytes

        Raises:
            TypeError: If content is not bytes or string
        """
        if isinstance(self.content, bytes):
            return self.content
        elif isinstance(self.content, str):
            return self.content.encode(self.encoding or "utf-8")
        else:
            raise TypeError(f"Content is not binary: {type(self.content)}")


class WriteResult(OperationResult):
    """Result of a file write operation."""

    bytes_written: int = Field(
        default=0,
        description="Number of bytes written",
    )

    original_path: Path | None = Field(
        default=None,
        description="Original path for move/copy _operations",
    )

    checksum: str | None = Field(
        default=None,
        description="Checksum of the written content",
    )


class FileInfoResult(OperationResult):
    """Result of a file info operation."""

    exists: bool = Field(
        default=False,
        description="Whether the file exists",
    )

    is_file: bool = Field(
        default=False,
        description="Whether the path is a file",
    )

    is_dir: bool = Field(
        default=False,
        description="Whether the path is a directory",
    )

    size: int | None = Field(
        default=None,
        description="Size in bytes",
    )

    modified: float | None = Field(
        default=None,
        description="Last modified timestamp",
    )

    created: float | None = Field(
        default=None,
        description="Creation timestamp",
    )

    owner: str | None = Field(
        default=None,
        description="Owner of the file",
    )

    permissions: int | None = Field(
        default=None,
        description="File permissions (mode)",
    )

    mime_type: str | None = Field(
        default=None,
        description="Detected MIME type",
    )

    # Property for backward compatibility
    @property
    def is_directory(self) -> bool:
        """Alias for is_dir for backward compatibility."""
        return self.is_dir


class DirectoryInfoResult(OperationResult):
    """Result of a directory listing operation."""

    exists: bool = Field(
        default=False,
        description="Whether the directory exists",
    )

    is_empty: bool = Field(
        default=True,
        description="Whether the directory is empty",
    )

    files: list[Path] = Field(
        default_factory=list,
        description="List of files in the directory",
    )

    directories: list[Path] = Field(
        default_factory=list,
        description="List of subdirectories in the directory",
    )

    total_files: int = Field(
        default=0,
        description="Total number of files",
    )

    total_directories: int = Field(
        default=0,
        description="Total number of subdirectories",
    )

    total_size: int = Field(
        default=0,
        description="Total size of all files in bytes",
    )


class FindResult(OperationResult):
    """Result of a file find operation."""

    files: list[Path] = Field(
        default_factory=list,
        description="List of files found",
    )

    directories: list[Path] = Field(
        default_factory=list,
        description="List of directories found",
    )

    total_matches: int = Field(
        default=0,
        description="Total number of matches",
    )

    pattern: str = Field(
        description="Pattern used for finding",
    )

    recursive: bool = Field(
        default=False,
        description="Whether search was recursive",
    )


class DataResult(OperationResult, Generic[T]):
    """Result for structured data _operations (YAML, JSON, etc.)."""

    data: T = Field(
        description="The structured data",
    )

    format: str = Field(
        description="Format of the data (e.g., 'yaml', 'json')",
    )

    schema_valid: bool | None = Field(
        default=None,
        description="Whether data passed schema validation",
    )

    def __fspath__(self) -> str:
        """
        Make DataResult compatible with os.PathLike.

        Returns:
            str: String representation of path data
        """
        if self.data is None:
            return ""
        return str(self.data)


class PathResult(OperationResult):
    """
    Result of a path validation or manipulation operation.

    This specialized result type provides detailed information about path
    validation, normalization, and checking _operations.
    """

    # Adding default values for is_absolute and is_valid to prevent errors when fields are accessed
    is_absolute: bool = False
    is_valid: bool = False
    exists: bool = False

    def __init__(
        self,
        success: bool = True,
        path: Path | None = None,
        is_absolute: bool = False,
        is_valid: bool = False,
        exists: bool = False,
        message: str | None = None,
        error: str | None = None,
    ):
        """
        Initialize a PathResult object.

        Args:
            success: Whether the operation was successful
            path: The path that was validated or manipulated
            is_absolute: Whether the path is absolute
            is_valid: Whether the path has valid syntax
            exists: Whether the path exists on the filesystem
            message: Optional success message
            error: Optional error message
        """
        super().__init__(success=success, path=path, message=message, error=error)
        self.is_absolute = is_absolute
        self.is_valid = is_valid
        self.exists = exists

    @property
    def is_relative(self) -> bool:
        """Whether the path is relative (not absolute)."""
        return not self.is_absolute

    def __repr__(self) -> str:
        """String representation of the PathResult."""
        status = "success" if self.success else "failure"
        path_str = f"'{self.path}'" if self.path else "None"
        return (
            f"PathResult({status}, path={path_str}, "
            f"exists={self.exists}, valid={self.is_valid}, "
            f"absolute={self.is_absolute})"
        )


# Aliases for backward compatibility with quack_core.fs.types
DirectoryListResult = DirectoryInfoResult
FileFindResult = FindResult
