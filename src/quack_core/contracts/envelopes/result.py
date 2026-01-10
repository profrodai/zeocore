# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/envelopes/result.py
# module: quack_core.contracts.envelopes.result
# role: module
# neighbors: __init__.py, error.py, log.py
# exports: CapabilityResult
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

"""
The canonical result envelope for all capabilities.

Consumed by: ALL Ring B tools, Ring C orchestrators (n8n, Temporal, runners)
Must NOT contain: Business logic, orchestration, side effects

This is the heart of the contracts system - every capability must return
a CapabilityResult to enable machine branching and audit trails.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from quack_core.contracts.common.enums import CapabilityStatus
from quack_core.contracts.common.ids import generate_run_id
from quack_core.contracts.common.time import utcnow
from quack_core.contracts.envelopes.error import CapabilityError
from quack_core.contracts.envelopes.log import CapabilityLogEvent

T = TypeVar("T")


class CapabilityResult(BaseModel, Generic[T]):
    """
    Standard return envelope for ALL capabilities.

    Orchestrators (n8n, Temporal) parse this JSON to decide the next step
    in the workflow. This enables:
    - Machine branching (success/skip/error paths)
    - Audit trails (logs, timing, metadata)
    - Debugging (structured errors with context)

    Invariants:
        - If status == error, then error must be present AND machine_message must be present
        - If status == error, then machine_message must start with QC_
        - If status == success, then error must be None AND machine_message should be None
        - If status == skipped, then error must be None AND machine_message must be present
        - If status == skipped, then machine_message must start with QC_
        - If machine_message is present, it must start with QC_

    Usage Pattern:
        Tools should use the helper methods (.ok(), .skip(), .fail()) rather
        than constructing CapabilityResult directly:

        >>> # Success
        >>> result = CapabilityResult.ok(
        ...     data={"transcription": "Hello world"},
        ...     msg="Transcription completed"
        ... )

        >>> # Skip
        >>> result = CapabilityResult.skip(
        ...     reason="Video too short for processing",
        ...     code="QC_VAL_TOO_SHORT"
        ... )

        >>> # Error
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     result = CapabilityResult.fail_from_exc(
        ...         msg="Failed to process video",
        ...         code="QC_IO_ERROR",
        ...         exc=e
        ...     )
    """

    model_config = ConfigDict(
        extra="forbid",  # Strict schema - no unexpected fields
    )

    # Core status
    status: CapabilityStatus = Field(
        ...,
        description="Execution status for machine branching"
    )

    # Payload (the actual value produced by the capability)
    data: T | None = Field(
        None,
        description="The actual result data (type varies by capability)"
    )

    # Telemetry
    run_id: str = Field(
        default_factory=generate_run_id,
        description="Unique identifier for this execution (should match RunManifest.run_id)"
    )

    timestamp: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when result was created"
    )

    duration_sec: float | None = Field(
        None,
        ge=0.0,
        description="Execution duration in seconds (None if not measured)"
    )

    # Messages
    human_message: str = Field(
        ...,
        description="Readable summary for logs/CLI/UI"
    )

    machine_message: str | None = Field(
        None,
        description="Machine-readable code for orchestrator branching (must start with QC_)"
    )

    # Diagnostics
    error: CapabilityError | None = Field(
        None,
        description="Structured error info if status == error"
    )

    logs: list[CapabilityLogEvent] = Field(
        default_factory=list,
        description="Structured log events from execution"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (tool, version, config, etc.)"
    )

    @field_validator("machine_message")
    @classmethod
    def validate_machine_message_format(cls, v: str | None) -> str | None:
        """Ensure machine_message follows QC_* convention when present."""
        if v is not None and not v.startswith("QC_"):
            raise ValueError(
                f"machine_message must start with 'QC_', got: {v}. "
                "Use format: QC_<AREA>_<DETAIL> (e.g., QC_VAL_TOO_SHORT)"
            )
        return v

    @model_validator(mode='after')
    def validate_status_invariants(self) -> 'CapabilityResult[T]':
        """
        Enforce invariants between status and other fields.

        This ensures orchestrators can rely on the structure:
        - Errors always have error objects and machine codes
        - Successes never have error objects or machine codes
        - Skips never have error objects but always have machine codes
        """
        if self.status == CapabilityStatus.error:
            if self.error is None:
                raise ValueError(
                    "status=error requires error field to be present"
                )
            if self.machine_message is None:
                raise ValueError(
                    "status=error requires machine_message for branching"
                )

        if self.status == CapabilityStatus.success:
            if self.error is not None:
                raise ValueError(
                    "status=success must not have error field"
                )
            if self.machine_message is not None:
                raise ValueError(
                    "status=success should not have machine_message "
                    "(success is the default path, no special routing needed)"
                )

        if self.status == CapabilityStatus.skipped:
            if self.error is not None:
                raise ValueError(
                    "status=skipped must not have error field "
                    "(skips are policy decisions, not errors)"
                )
            if self.machine_message is None:
                raise ValueError(
                    "status=skipped requires machine_message for branching"
                )

        return self

    # Convenience constructors

    @classmethod
    def ok(
            cls,
            data: T,
            msg: str = "Success",
            metadata: dict[str, Any] | None = None,
            logs: list[CapabilityLogEvent] | None = None,
            duration_sec: float | None = None,
            run_id: str | None = None
    ) -> "CapabilityResult[T]":
        """
        Create a successful result.

        Args:
            data: The result payload
            msg: Human-readable success message
            metadata: Optional metadata dict
            logs: Optional log events from execution
            duration_sec: Execution time in seconds (None if not measured)
            run_id: Optional run_id to reuse (should match manifest run_id)

        Returns:
            CapabilityResult with status=success

        Example:
            >>> result = CapabilityResult.ok(
            ...     data={"clips": [...]},
            ...     msg="Generated 5 clips",
            ...     metadata={"tool": "slice_video", "preset": "fast"}
            ... )
        """
        kwargs = {
            "status": CapabilityStatus.success,
            "data": data,
            "human_message": msg,
            "metadata": metadata or {},
            "logs": logs or [],
            "duration_sec": duration_sec
        }
        if run_id is not None:
            kwargs["run_id"] = run_id
        return cls(**kwargs)

    @classmethod
    def skip(
            cls,
            reason: str,
            code: str,
            metadata: dict[str, Any] | None = None,
            run_id: str | None = None
    ) -> "CapabilityResult[T]":
        """
        Create a skip result (valid policy decision).

        Skips are NOT errors - they represent intentional decisions
        to skip processing (e.g., video too short, file already exists).

        Args:
            reason: Human-readable explanation for the skip
            code: Machine-readable skip code (must start with QC_)
            metadata: Optional metadata dict
            run_id: Optional run_id to reuse (should match manifest run_id)

        Returns:
            CapabilityResult with status=skipped

        Example:
            >>> result = CapabilityResult.skip(
            ...     reason="Video duration under 10 seconds",
            ...     code="QC_VAL_TOO_SHORT"
            ... )
        """
        kwargs = {
            "status": CapabilityStatus.skipped,
            "human_message": reason,
            "machine_message": code,
            "metadata": metadata or {}
        }
        if run_id is not None:
            kwargs["run_id"] = run_id
        return cls(**kwargs)

    @classmethod
    def fail(
            cls,
            msg: str,
            code: str,
            exception: Exception | None = None,
            metadata: dict[str, Any] | None = None,
            logs: list[CapabilityLogEvent] | None = None,
            run_id: str | None = None
    ) -> "CapabilityResult[T]":
        """
        Create an error result.

        Args:
            msg: Human-readable error message
            code: Machine-readable error code (must start with QC_)
            exception: Optional exception that caused the error
            metadata: Optional metadata dict
            logs: Optional log events from execution
            run_id: Optional run_id to reuse (should match manifest run_id)

        Returns:
            CapabilityResult with status=error

        Example:
            >>> result = CapabilityResult.fail(
            ...     msg="Failed to read video file",
            ...     code="QC_IO_NOT_FOUND",
            ...     exception=FileNotFoundError("/data/video.mp4")
            ... )
        """
        err_details: dict[str, Any] = {}
        if exception:
            err_details = {
                "type": type(exception).__name__,
                "str": str(exception),
            }

        kwargs = {
            "status": CapabilityStatus.error,
            "human_message": msg,
            "machine_message": code,
            "error": CapabilityError(code=code, message=msg, details=err_details),
            "metadata": metadata or {},
            "logs": logs or []
        }
        if run_id is not None:
            kwargs["run_id"] = run_id
        return cls(**kwargs)

    @classmethod
    def fail_from_exc(
            cls,
            msg: str,
            code: str,
            exc: Exception,
            metadata: dict[str, Any] | None = None,
            run_id: str | None = None
    ) -> "CapabilityResult[T]":
        """
        Convenience wrapper for fail() that always includes exception.

        Args:
            msg: Human-readable error message
            code: Machine-readable error code (must start with QC_)
            exc: Exception that caused the error
            metadata: Optional metadata dict
            run_id: Optional run_id to reuse (should match manifest run_id)

        Returns:
            CapabilityResult with status=error

        Example:
            >>> try:
            ...     process_video()
            ... except IOError as e:
            ...     result = CapabilityResult.fail_from_exc(
            ...         msg="Video processing failed",
            ...         code="QC_IO_ERROR",
            ...         exc=e
            ...     )
        """
        return cls.fail(msg=msg, code=code, exception=exc, metadata=metadata, run_id=run_id)
