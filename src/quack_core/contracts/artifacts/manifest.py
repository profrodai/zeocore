# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/artifacts/manifest.py
# module: quack_core.contracts.artifacts.manifest
# role: module
# neighbors: __init__.py, refs.py
# exports: ToolInfo, Provenance, ManifestInput, RunManifest
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Run manifest models for tracking capability execution.

Consumed by: Ring C orchestrators (n8n, Temporal, QuackRunner)
Must NOT contain: Workflow logic, orchestration, file I/O

The RunManifest is the complete record of a tool execution:
inputs, outputs, logs, errors, timing, and provenance.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from quack_core.contracts.artifacts.refs import ArtifactRef
from quack_core.contracts.common.enums import CapabilityStatus
from quack_core.contracts.common.ids import generate_run_id, is_valid_uuid
from quack_core.contracts.common.time import utcnow
from quack_core.contracts.common.versions import MANIFEST_VERSION
from quack_core.contracts.envelopes.error import CapabilityError
from quack_core.contracts.envelopes.log import CapabilityLogEvent


class ToolInfo(BaseModel):
    """
    Information about the tool that executed.

    Used for debugging and version tracking.

    Tool Naming Convention:
        Use namespaced tool names for clarity across capability domains:
        - media.slice_video
        - media.transcribe
        - text.summarize
        - text.extract_entities
        - crm.sync_contacts
        - fs.copy_files
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        description="Tool identifier with namespace (e.g., 'media.slice_video', 'text.summarize')",
        examples=["media.slice_video", "text.summarize", "crm.sync_contacts"]
    )

    version: str = Field(
        ...,
        description="Tool version (semver recommended)"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional tool info (runtime, config, etc.)"
    )


class Provenance(BaseModel):
    """
    Provenance information for reproducibility.

    Tracks where, when, and how the execution occurred.
    All fields are optional to support different execution environments.
    """

    model_config = ConfigDict(extra="forbid")

    git_commit: str | None = Field(
        None,
        description="Git commit SHA of the code"
    )

    git_branch: str | None = Field(
        None,
        description="Git branch name"
    )

    git_repo: str | None = Field(
        None,
        description="Git repository URL"
    )

    host: str | None = Field(
        None,
        description="Hostname where execution occurred"
    )

    user: str | None = Field(
        None,
        description="User who triggered execution"
    )

    environment: str | None = Field(
        None,
        description="Execution environment (local, dev, staging, prod)",
        examples=["local", "dev", "staging", "prod"]
    )

    runner: str | None = Field(
        None,
        description="Runner that executed the tool (cli, n8n, temporal)",
        examples=["cli", "n8n", "temporal", "lambda"]
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provenance data"
    )


class ManifestInput(BaseModel):
    """
    Wrapper for input artifacts with additional semantics.

    Provides more context than a bare ArtifactRef when needed.
    """

    model_config = ConfigDict(extra="forbid")

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

    description: str | None = Field(
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
        - If status == skipped → outputs AND intermediates must be empty
        - If status == error → outputs AND intermediates must be empty (no partial outputs)
        - error field required if status == error

    Routing Convention:
        Orchestrators should NOT inspect file contents. Instead, route by:
        - outputs[*].role (semantic meaning)
        - outputs[*].kind (intermediate vs final)
        - outputs[*].content_type (format)
        - outputs[*].tags (additional hints)

    Run ID Relationship:
        The run_id should be generated once and shared between:
        - CapabilityResult.run_id (immediate return)
        - RunManifest.run_id (persistent record)
        Tools should pass the same run_id to both.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                # Media capability example
                {
                    "manifest_version": "1.0",
                    "run_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tool": {
                        "name": "media.slice_video",
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
                                "artifact_id": "a1b2c3d4-e5f6-4789-abcd-ef0123456789",
                                "role": "media.video_source",
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
                            "artifact_id": "b2c3d4e5-f678-49ab-cdef-0123456789ab",
                            "role": "media.video_slice_1",
                            "kind": "final",
                            "content_type": "video/mp4",
                            "storage": {
                                "scheme": "local",
                                "uri": "file:///data/output/clip1.mp4"
                            }
                        }
                    ],
                    "intermediates": [],
                    "logs": [],
                    "metadata": {
                        "preset": "fast",
                        "clip_count": 1
                    }
                },
                # Text capability example
                {
                    "manifest_version": "1.0",
                    "run_id": "c3d4e5f6-7890-4abc-def0-123456789abc",
                    "tool": {
                        "name": "text.summarize",
                        "version": "2.1.0"
                    },
                    "started_at": "2025-01-15T11:00:00Z",
                    "finished_at": "2025-01-15T11:00:12Z",
                    "duration_sec": 12.0,
                    "status": "success",
                    "inputs": [
                        {
                            "name": "source_document",
                            "artifact": {
                                "artifact_id": "d4e5f678-90ab-4cde-f012-3456789abcde",
                                "role": "text.document_md",
                                "kind": "intermediate",
                                "content_type": "text/markdown",
                                "storage": {
                                    "scheme": "local",
                                    "uri": "file:///data/document.md"
                                }
                            },
                            "required": True
                        }
                    ],
                    "outputs": [
                        {
                            "artifact_id": "e5f67890-abcd-4ef0-1234-56789abcdef0",
                            "role": "text.summary_md",
                            "kind": "final",
                            "content_type": "text/markdown",
                            "storage": {
                                "scheme": "local",
                                "uri": "file:///data/output/summary.md"
                            }
                        }
                    ],
                    "intermediates": [],
                    "logs": [],
                    "metadata": {
                        "model": "llm:anthropic:claude-sonnet",
                        "max_tokens": 500
                    }
                },
                # CRM integration example
                {
                    "manifest_version": "1.0",
                    "run_id": "f6789abc-def0-4123-4567-89abcdef0123",
                    "tool": {
                        "name": "crm.sync_contacts",
                        "version": "1.2.3"
                    },
                    "started_at": "2025-01-15T12:00:00Z",
                    "finished_at": "2025-01-15T12:01:30Z",
                    "duration_sec": 90.0,
                    "status": "success",
                    "inputs": [
                        {
                            "name": "contacts_csv",
                            "artifact": {
                                "artifact_id": "789abcde-f012-4345-6789-abcdef012345",
                                "role": "crm.contacts_csv",
                                "kind": "intermediate",
                                "content_type": "text/csv",
                                "storage": {
                                    "scheme": "local",
                                    "uri": "file:///data/contacts.csv"
                                }
                            },
                            "required": True
                        }
                    ],
                    "outputs": [
                        {
                            "artifact_id": "890abcde-f012-4567-89ab-cdef01234567",
                            "role": "crm.sync_report_json",
                            "kind": "report",
                            "content_type": "application/json",
                            "storage": {
                                "scheme": "local",
                                "uri": "file:///data/output/sync_report.json"
                            }
                        }
                    ],
                    "intermediates": [],
                    "logs": [],
                    "metadata": {
                        "synced_count": 150,
                        "failed_count": 2,
                        "crm_system": "salesforce"
                    }
                }
            ]
        }
    )

    # Schema version
    manifest_version: str = Field(
        default=MANIFEST_VERSION,
        description="Schema version for forward compatibility"
    )

    # Execution identity
    run_id: str = Field(
        default_factory=generate_run_id,
        description="Unique identifier for this execution (should match CapabilityResult.run_id)"
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

    finished_at: datetime | None = Field(
        None,
        description="UTC timestamp when execution finished"
    )

    duration_sec: float | None = Field(
        None,
        ge=0.0,
        description="Execution duration in seconds (None if not measured)"
    )

    # Status
    status: CapabilityStatus = Field(
        ...,
        description="Execution status (success, skipped, error)"
    )

    # Artifacts
    inputs: list[ManifestInput] = Field(
        default_factory=list,
        description="Input artifacts consumed by the tool"
    )

    outputs: list[ArtifactRef] = Field(
        default_factory=list,
        description="Output artifacts produced by the tool"
    )

    intermediates: list[ArtifactRef] = Field(
        default_factory=list,
        description="Intermediate artifacts (may be cleaned up)"
    )

    # Diagnostics (reuse envelope models)
    logs: list[CapabilityLogEvent] = Field(
        default_factory=list,
        description="Structured log events from execution"
    )

    error: CapabilityError | None = Field(
        None,
        description="Structured error if status == error"
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form metadata (config, environment, capability-specific data)"
    )

    provenance: Provenance | None = Field(
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
        Enforce invariants between status and artifact lists.

        - If status == error, error field must be present
        - If status == skipped or error, outputs AND intermediates must be empty

        Rationale: skipped/error statuses indicate the tool did not complete
        successfully, so no artifacts should be produced. This keeps orchestrator
        routing logic simple: only success statuses produce artifacts to route.
        """
        if self.status == CapabilityStatus.error:
            if self.error is None:
                raise ValueError(
                    "status=error requires error field to be present"
                )
            if self.outputs:
                raise ValueError(
                    "status=error must have empty outputs (no partial outputs allowed)"
                )
            if self.intermediates:
                raise ValueError(
                    "status=error must have empty intermediates (no partial artifacts allowed)"
                )

        if self.status == CapabilityStatus.skipped:
            if self.outputs:
                raise ValueError(
                    "status=skipped must have empty outputs (skipped processing produces no outputs)"
                )
            if self.intermediates:
                raise ValueError(
                    "status=skipped must have empty intermediates (skipped processing produces no artifacts)"
                )

        return self
