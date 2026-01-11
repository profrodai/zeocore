# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/results.py
# module: quack_core.core.fs.results
# role: module
# neighbors: __init__.py, protocols.py, plugin.py, normalize.py
# exports: ErrorInfo, OperationResult, ReadResult, WriteResult, FileInfoResult, DirectoryInfoResult, FindResult, DataResult (+1 more)
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

from pathlib import Path
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field, field_serializer, computed_field

T = TypeVar("T")

class ErrorInfo(BaseModel):
    """Structured error information."""
    type: str = Field(description="Error type identifier (e.g. 'FileNotFoundError')")
    message: str = Field(description="Original exception message")
    hint: Optional[str] = Field(default=None, description="User-friendly resolution hint")
    exception: Optional[str] = Field(default=None, description="Stringified exception class")
    trace_id: Optional[str] = Field(default=None, description="Tracing identifier for debugging")
    details: Optional[dict] = Field(default=None, description="Structured context (path, errno, etc)")

class OperationResult(BaseModel):
    success: bool = Field(description="Whether the operation was successful")
    path: Path | None = Field(default=None, description="Path operated on (normalized)")
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
    def text(self) -> str | None:
        """Safe access to text content. Returns None if invalid type/missing."""
        if isinstance(self.content, str):
            return self.content
        if isinstance(self.content, bytes):
            try:
                return self.content.decode(self.encoding or "utf-8")
            except Exception:
                return None
        return None

    @property
    def binary(self) -> bytes | None:
        """Safe access to binary content. Returns None if invalid type/missing."""
        if isinstance(self.content, bytes):
            return self.content
        if isinstance(self.content, str):
            try:
                return self.content.encode(self.encoding or "utf-8")
            except Exception:
                return None
        return None

    def as_text(self, default: str = "") -> str:
        """Explicit coercion helper."""
        return self.text if self.text is not None else default

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