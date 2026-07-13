# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/results.py
# module: quack_core.core.fs.results
# role: module
# neighbors: __init__.py, protocols.py, plugin.py, exceptions.py, normalize.py
# exports: ErrorInfo, OperationResult, BoolResult, ReadResult, WriteResult, FileInfoResult, DirectoryInfoResult, FindResult (+2 more)
# git_branch: feat/9-make-setup-work
# git_commit: f4879df3
# === QV-LLM:END ===

from pathlib import Path
from typing import Any, Generic, TypeVar, Optional
from pydantic import (
    BaseModel, Field, FieldSerializationInfo, field_serializer, computed_field,
)

T = TypeVar("T")


class ErrorInfo(BaseModel):
    """Structured error information."""
    type: str = Field(description="Error type identifier (e.g. 'file_not_found')")
    message: str = Field(description="Original exception message")
    hint: Optional[str] = Field(default=None, description="User-friendly resolution hint")
    exception: Optional[str] = Field(default=None, description="Exception class name")
    trace_id: Optional[str] = Field(default=None, description="Tracing identifier for debugging")
    details: Optional[dict[str, Any]] = Field(
        default=None, description="Structured context (path, errno, etc)"
    )


class OperationResult(BaseModel):
    """
    Base result for filesystem operations.

    Fields:
        ok: Primary success indicator (canonical)
        path: Normalized path (None on failure to prevent unsafe path leaks)
        error_info: Structured error details (canonical error representation)
        meta: Additional operation metadata
        message: Human-readable summary (success or failure)
        error: Legacy string error (deprecated - use error_info instead)
    """
    ok: bool = Field(description="Whether the operation was successful (canonical)")
    path: Path | None = Field(default=None, description="Path operated on (normalized, None on failure)")
    message: str | None = Field(default=None, description="Human-readable operation summary")
    error: str | None = Field(default=None, description="LEGACY: Use error_info instead")
    error_info: ErrorInfo | None = Field(default=None, description="Structured error details (canonical)")
    meta: dict[str, Any] | None = Field(
        default=None, description="Additional operation metadata"
    )


    @computed_field  # type: ignore[prop-decorator]  # pydantic computed_field+property, mypy limitation
    @property
    def success(self) -> bool:
        """DEPRECATED - use .ok. Transitional R-1 alias delegating to the canonical
        field; removed once a whole-tree audit shows zero .success readers on core/fs
        results (migrate-fs-result-consumers-to-ok charter). Do not add new readers."""
        return self.ok

    @field_serializer('path')
    def serialize_path(
        self, path: Path | None, _info: FieldSerializationInfo
    ) -> str | None:
        return str(path) if path else None


class BoolResult(OperationResult):
    """Result of a boolean check operation (e.g. exists, is_file)."""
    value: bool = Field(description="The boolean result")

    def __bool__(self) -> bool:
        return self.value


class ReadResult(OperationResult, Generic[T]):
    """Result of a read operation."""
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
    """Result of a write operation."""
    bytes_written: int = 0
    original_path: Path | None = None
    checksum: str | None = None

    @field_serializer('original_path')
    def serialize_original_path(
        self, path: Path | None, _info: FieldSerializationInfo
    ) -> str | None:
        return str(path) if path else None


class FileInfoResult(OperationResult):
    """Result of file metadata query."""
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
    """Result of directory listing/scan."""
    exists: bool = False
    is_empty: bool = True
    files: list[Path] = Field(default_factory=list)
    directories: list[Path] = Field(default_factory=list)
    total_files: int = 0
    total_directories: int = 0
    total_size: int = 0

    @field_serializer('files', 'directories')
    def serialize_path_lists(
        self, paths: list[Path], _info: FieldSerializationInfo
    ) -> list[str]:
        return [str(p) for p in paths]


class FindResult(OperationResult):
    """Result of file search operation."""
    files: list[Path] = Field(default_factory=list)
    directories: list[Path] = Field(default_factory=list)
    total_matches: int = 0
    pattern: str
    recursive: bool = False

    @field_serializer('files', 'directories')
    def serialize_path_lists(
        self, paths: list[Path], _info: FieldSerializationInfo
    ) -> list[str]:
        return [str(p) for p in paths]


class DataResult(OperationResult, Generic[T]):
    """
    Result containing structured data.

    Fields:
        data: The payload (can be any type: dict, list, str, etc.)
        format: Data format identifier (e.g. 'yaml', 'json', 'path', 'boolean')
        schema_valid: Whether data passed schema validation (optional)
    """
    data: T | None = None
    format: str = Field(default="data", description="Data format identifier")
    schema_valid: bool | None = None


class PathResult(OperationResult):
    """
    Result of path validation/normalization/resolution.

    Field Semantics:
        is_valid: True if path passed service normalization + sandbox checks
                  (i.e., coerce_path succeeded). False if validation failed.
        is_absolute: True if the normalized path is absolute.
        exists: True if the path exists on the filesystem (optional check).

    Note: is_valid_path() returns BoolResult with syntax-only validation.
          PathResult.is_valid indicates full service-level validation success.
    """
    is_absolute: bool = False
    is_valid: bool = Field(
        default=False,
        description="True if service normalization + sandbox validation succeeded"
    )
    exists: bool = Field(
        default=False,
        description="True if path exists on filesystem (checked if validation succeeded)"
    )

    @computed_field  # type: ignore[prop-decorator]  # pydantic computed_field+property, mypy limitation
    @property
    def is_relative(self) -> bool:
        """Computed: opposite of is_absolute."""
        return not self.is_absolute