"""Portable facts shared by conversion and execution receipts."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ArtifactFact(BaseModel):
    """Content identity; paths are relative unless explicitly requested otherwise."""

    model_config = ConfigDict(frozen=True)
    path: str
    format: str
    size_bytes: int
    sha256: str


class NotebookCellFact(BaseModel):
    """Semantic cell identity without source or output contents."""

    ordinal: int
    cell_type: Literal["markdown", "code", "raw"]
    cell_id: str | None
    tags: tuple[str, ...]
    source_sha256: str
    metadata_sha256: str
    attachments_sha256: str


class ConversionReceipt(BaseModel):
    """Conversion evidence. Structural validity never constitutes visual approval."""

    integration_id: str
    integration_version: str = "1.0.0"
    converter_version: str
    source: ArtifactFact
    output: ArtifactFact | None = None
    cells: tuple[NotebookCellFact, ...] | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    status: Literal["SUCCEEDED", "FAILED"]
    structural_validation: Literal["PASSED", "FAILED", "UNAVAILABLE"]
    human_visual_approval: Literal[False] = False
    intended_use: Literal["DERIVED_ARTIFACT", "REVIEW_DRAFT"] = "DERIVED_ARTIFACT"

    def reproducibility_digest(self) -> str:
        """Hash portable facts, excluding the named conversion-time diagnostic."""
        payload = self.model_dump(mode="json")
        payload["details"].pop("conversion_time", None)
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class RequiredConversionTask(BaseModel):
    """A stable task with an explicit destination relative to its release directory."""

    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1)
    source_path: str
    output_path: str
    target_format: str
    required: bool = True


class ConversionBatchItem(BaseModel):
    """One ordered result for every requested task, including failures."""

    task_id: str
    required: bool
    status: Literal["SUCCEEDED", "FAILED", "NOT_RUN"]
    receipt: ConversionReceipt | None = None
    error: str | None = None


class ConversionBatchReceipt(BaseModel):
    """A directory promotion transaction, not a list of files that happened to work."""

    items: tuple[ConversionBatchItem, ...]
    status: Literal["SUCCEEDED", "FAILED"]
    promoted: bool = False
    output_directory: str
    failure_policy: Literal["CLEAN"] = "CLEAN"


def artifact_fact(
    path: Path, format_name: str, workspace_root: Path, *, absolute_paths: bool = False
) -> ArtifactFact:
    """Hash the full bytes and refuse paths outside the declared workspace."""
    resolved = path.resolve(strict=True)
    portable = (
        resolved if absolute_paths else resolved.relative_to(workspace_root.resolve())
    )
    data = resolved.read_bytes()
    return ArtifactFact(
        path=str(portable),
        format=format_name,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def validate_output(source: Path, output: Path, root: Path) -> None:
    """Refuse aliases, traversal, symlinks and collisions before any write."""
    root = root.resolve(strict=True)
    if ".." in source.parts or ".." in output.parts:
        raise ValueError("PATH_TRAVERSAL")
    source.resolve(strict=True).relative_to(root)
    output.resolve().relative_to(root)
    for candidate in (source, output):
        current = candidate.absolute()
        while current != root and current != current.parent:
            if current.is_symlink():
                raise ValueError("SYMLINK_PATH")
            current = current.parent
    if source.resolve() == output.resolve():
        raise ValueError("SOURCE_OUTPUT_ALIAS")
    if output.exists() or output.is_symlink():
        raise ValueError("OUTPUT_EXISTS")
