# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/artifacts/manifest.py
# module: quack_core.contracts.artifacts.manifest
# role: module
# neighbors: __init__.py, refs.py
# exports: ToolInfo, Provenance, ManifestInput, RunManifest
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Run manifest models for tracking capability execution.

Consumed by: Ring C orchestrators (n8n, Temporal, QuackRunner)
Must NOT contain: Workflow logic, orchestration, file I/O

The RunManifest is the complete record of a tool execution:
inputs, outputs, logs, errors, timing, and provenance.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict

from quack_core.contracts.common.enums import CapabilityStatus
from quack_core.contracts.common.ids import generate_run_id, is_valid_uuid
from quack_core.contracts.common.time import utcnow
from quack_core.contracts.common.versions import MANIFEST_VERSION
from quack_core.contracts.envelopes.log import CapabilityLogEvent
from quack_core.contracts.envelopes.error import CapabilityError
from quack_core.contracts.artifacts.refs import ArtifactRef


class ToolInfo(BaseModel):
    """
    Information about the tool that executed.

    Used for debugging and version tracking.
    """

    name: str = Field(
        ...,
        description="Tool identifier (e.g., 'slice_video', 'transcribe_audio')"
    )

    version: str = Field(
        ...,
        description="Tool version (semver recommended)"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional tool info (runtime, config, etc.)"
    )


class Provenance(BaseModel):
    """
    Provenance information for reproducibility.

    Tracks where, when, and how the execution occurred.
    All fields are optional to support different execution environments.
    """

    git_commit: Optional[str] = Field(
        None,
        description="Git commit SHA of the code"
    )

    git_branch: Optional[str] = Field(
        None,
        description="Git branch name"
    )

    git_repo: Optional[str] = Field(
        None,
        description="Git repository URL"
    )

    host: Optional[str] = Field(
        None,
        description="Hostname where execution occurred"
    )

    user: Optional[str] = Field(
        None,
        description="User who triggered execution"
    )

    environment: Optional[str] = Field(
        None,
        description="Execution environment (local, dev, staging, prod)",
        examples=["local", "dev", "staging", "prod"]
    )

    runner: Optional[str] = Field(
        None,
        description="Runner that executed the tool (cli, n8n, temporal)",
        examples=["cli", "n8n", "temporal", "lambda"]
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provenance data"
    )


class ManifestInput(BaseModel):
    """
    Wrapper for input artifacts with additional semantics.

    Provides more context than a bare ArtifactRef when needed.
    """

    name: str = Field(
        ...,
        description="Input parameter name"
    )

    artifact: ArtifactRef = Field(
        ...,
        description="Reference to the input artifact"
    )

    required: bool = Field(
        default=True,
        description="Whether this input is required for the tool"
    )

    description: Optional[str] = Field(
        None,
        description="Human-readable description of this input"
    )


class RunManifest(BaseModel):
    """
    Complete record of a capability execution.

    The manifest is the "contract" between tools and orchestrators:
    - Tools emit manifests after execution
    - Orchestrators read manifests to route artifacts
    - Monitoring systems read manifests for observability

    Invariants:
        - finished_at >= started_at (if both present)
        - duration_sec consistent with timestamps (if all present)
        - outputs empty if status == skipped (convention, not enforced)

    Routing Convention:
        Orchestrators should NOT inspect file contents. Instead, route by:
        - outputs[*].role (semantic meaning)
        - outputs[*].kind (intermediate vs final)
        - outputs[*].content_type (format)
        - outputs[*].tags (additional hints)

    Example:
        >>> manifest = RunManifest(
        ...     tool=ToolInfo(name="slice_video", version="1.0.0"),
        ...     status=CapabilityStatus.success,
        ...     inputs=[
        ...         ManifestInput(
        ...             name="source_video",
        ...             artifact=ArtifactRef(
        ...                 role="video_source",
        ...                 kind=ArtifactKind.intermediate,
        ...                 content_type="video/mp4",
        ...                 storage=StorageRef(...)
        ...             )
        ...         )
        ...     ],
        ...     outputs=[
        ...         ArtifactRef(
        ...             role="video_slice_1",
        ...             kind=ArtifactKind.final,
        ...             content_type="video/mp4",
        ...             storage=StorageRef(...)
        ...         )
        ...     ]
        ... )
    """

    # Schema version
    manifest_version: str = Field(
        default=MANIFEST_VERSION,
        description="Schema version for forward compatibility"
    )

    # Execution identity
    run_id: str = Field(
        default_factory=generate_run_id,
        description="Unique identifier for this execution"
    )

    tool: ToolInfo = Field(
        ...,
        description="Information about the tool that executed"
    )

    # Timing
    started_at: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when execution started"
    )

    finished_at: Optional[datetime] = Field(
        None,
        description="UTC timestamp when execution finished"
    )

    duration_sec: Optional[float] = Field(
        None,
        ge=0.0,
        description="Execution duration in seconds"
    )

    # Status
    status: CapabilityStatus = Field(
        ...,
        description="Execution status (success, skipped, error)"
    )

    # Artifacts
    inputs: List[ManifestInput] = Field(
        default_factory=list,
        description="Input artifacts consumed by the tool"
    )

    outputs: List[ArtifactRef] = Field(
        default_factory=list,
        description="Output artifacts produced by the tool"
    )

    intermediates: List[ArtifactRef] = Field(
        default_factory=list,
        description="Intermediate artifacts (may be cleaned up)"
    )

    # Diagnostics (reuse envelope models)
    logs: List[CapabilityLogEvent] = Field(
        default_factory=list,
        description="Structured log events from execution"
    )

    error: Optional[CapabilityError] = Field(
        None,
        description="Structured error if status == error"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form metadata (config, environment, etc.)"
    )

    provenance: Optional[Provenance] = Field(
        None,
        description="Provenance info for reproducibility"
    )

    @field_validator("run_id")
    @classmethod
    def validate_run_id_format(cls, v: str) -> str:
        """Ensure run_id is a valid UUID."""
        if not is_valid_uuid(v):
            raise ValueError(f"run_id must be a valid UUID, got: {v}")
        return v

    @model_validator(mode='after')
    def validate_timing_consistency(self) -> 'RunManifest':
        """
        Ensure timing fields are consistent.

        - finished_at must be >= started_at
        - duration_sec should match timestamps if all present
        """
        if self.finished_at is not None:
            if self.finished_at < self.started_at:
                raise ValueError(
                    f"finished_at ({self.finished_at}) must be >= started_at ({self.started_at})"
                )

            # Validate duration_sec if present
            if self.duration_sec is not None:
                actual_duration = (self.finished_at - self.started_at).total_seconds()
                # Allow small tolerance for floating point
                if abs(actual_duration - self.duration_sec) > 0.1:
                    raise ValueError(
                        f"duration_sec ({self.duration_sec}) inconsistent with "
                        f"timestamps (actual: {actual_duration})"
                    )

        return self

    @model_validator(mode='after')
    def validate_status_invariants(self) -> 'RunManifest':
        """
        Enforce invariants between status and other fields.

        - If status == error, error field must be present
        """
        if self.status == CapabilityStatus.error:
            if self.error is None:
                raise ValueError(
                    "status=error requires error field to be present"
                )

        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "manifest_version": "1.0",
                    "run_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tool": {
                        "name": "slice_video",
                        "version": "1.0.0"
                    },
                    "started_at": "2025-01-15T10:30:00Z",
                    "finished_at": "2025-01-15T10:30:45Z",
                    "duration_sec": 45.0,
                    "status": "success",
                    "inputs": [
                        {
                            "name": "source_video",
                            "artifact": {
                                "artifact_id": "abc-123",
                                "role": "video_source",
                                "kind": "intermediate",
                                "content_type": "video/mp4",
                                "storage": {
                                    "scheme": "local",
                                    "uri": "file:///data/input.mp4"
                                }
                            },
                            "required": True
                        }
                    ],
                    "outputs": [
                        {
                            "artifact_id": "def-456",
                            "role": "video_slice_1",
                            "kind": "final",
                            "content_type": "video/mp4",
                            "storage": {
                                "scheme": "local",
                                "uri": "file:///data/output/clip1.mp4"
                            }
                        }
                    ],
                    "logs": [],
                    "metadata": {
                        "preset": "fast",
                        "clip_count": 1
                    }
                }
            ]
        }
    )