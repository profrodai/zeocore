from pathlib import Path
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field, field_serializer, computed_field

T = TypeVar("T")

class ErrorInfo(BaseModel):
    """Structured error information."""
    type: str = Field(description="Error type identifier (e.g. 'FileNotFoundError')")
    message: str = Field(description="Human-readable error message")
    hint: Optional[str] = Field(default=None, description="Optional hint for resolution")
    exception: Optional[str] = Field(default=None, description="Stringified exception class")

class OperationResult(BaseModel):
    success: bool = Field(description="Whether the operation was successful")
    path: Path | None = Field(default=None, description="Path operated on")
    message: str | None = Field(default=None)
    error: str | None = Field(default=None, description="Legacy error string")
    error_info: ErrorInfo | None = Field(default=None, description="Structured error details")

    @computed_field
    @property
    def ok(self) -> bool:
        """Alias for success."""
        return self.success

    @field_serializer('path')
    def serialize_path(self, path: Path | None, _info):
        return str(path) if path else None

class ReadResult(OperationResult, Generic[T]):
    content: T | None = Field(default=None, description="Content read from file")
    encoding: str | None = None

    @property
    def text(self) -> str:
        if self.content is None:
            raise ValueError("No content available")
        if isinstance(self.content, str):
            return self.content
        if isinstance(self.content, bytes):
            return self.content.decode(self.encoding or "utf-8")
        raise TypeError(f"Content is not text: {type(self.content)}")

    @property
    def binary(self) -> bytes:
        if self.content is None:
            raise ValueError("No content available")
        if isinstance(self.content, bytes):
            return self.content
        if isinstance(self.content, str):
            return self.content.encode(self.encoding or "utf-8")
        raise TypeError(f"Content is not binary: {type(self.content)}")

class WriteResult(OperationResult):
    bytes_written: int = 0
    original_path: Path | None = None
    checksum: str | None = None

    @field_serializer('original_path')
    def serialize_original_path(self, path: Path | None, _info):
        return str(path) if path else None

class FileInfoResult(OperationResult):
    exists: bool = False
    is_file: bool = False
    is_dir: bool = False
    size: int | None = None
    modified: float | None = None
    created: float | None = None
    modified_iso: str | None = None
    created_iso: str | None = None
    owner: str | None = None
    permissions: int | None = None
    mime_type: str | None = None

    @property
    def is_directory(self) -> bool:
        return self.is_dir

class DirectoryInfoResult(OperationResult):
    exists: bool = False
    is_empty: bool = True
    files: list[Path] = Field(default_factory=list)
    directories: list[Path] = Field(default_factory=list)
    total_files: int = 0
    total_directories: int = 0
    total_size: int = 0

    @field_serializer('files', 'directories')
    def serialize_path_lists(self, paths: list[Path], _info):
        return [str(p) for p in paths]

class FindResult(OperationResult):
    files: list[Path] = Field(default_factory=list)
    directories: list[Path] = Field(default_factory=list)
    total_matches: int = 0
    pattern: str
    recursive: bool = False

    @field_serializer('files', 'directories')
    def serialize_path_lists(self, paths: list[Path], _info):
        return [str(p) for p in paths]

class DataResult(OperationResult, Generic[T]):
    data: T
    format: str
    schema_valid: bool | None = None

class PathResult(OperationResult):
    is_absolute: bool = False
    is_valid: bool = False
    exists: bool = False

    @computed_field
    @property
    def is_relative(self) -> bool:
        return not self.is_absolute