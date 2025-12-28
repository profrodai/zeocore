# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/envelopes/result.py
# module: quack_core.contracts.envelopes.result
# role: module
# neighbors: __init__.py, error.py, log.py
# exports: CapabilityResult
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
The canonical result envelope for all capabilities.

Consumed by: ALL Ring B tools, Ring C orchestrators (n8n, Temporal, runners)
Must NOT contain: Business logic, orchestration, side effects

This is the heart of the contracts system - every capability must return
a CapabilityResult to enable machine branching and audit trails.
"""

from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, ConfigDict

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
        - If status == error, then error must be present
        - If status == error, then machine_message must be present
        - If status == success, then error must be None
        - If status == skipped, data may be None (skips produce no output)

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

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core status
    status: CapabilityStatus = Field(
        ...,
        description="Execution status for machine branching"
    )

    # Payload (the actual value produced by the capability)
    data: Optional[T] = Field(
        None,
        description="The actual result data (type varies by capability)"
    )

    # Telemetry
    run_id: str = Field(
        default_factory=generate_run_id,
        description="Unique identifier for this execution"
    )

    timestamp: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when result was created"
    )

    duration_sec: float = Field(
        default=0.0,
        ge=0.0,
        description="Execution duration in seconds"
    )

    # Messages
    human_message: str = Field(
        ...,
        description="Readable summary for logs/CLI/UI"
    )

    machine_message: Optional[str] = Field(
        None,
        description="Machine-readable code for orchestrator branching (QC_* format)"
    )

    # Diagnostics
    error: Optional[CapabilityError] = Field(
        None,
        description="Structured error info if status == error"
    )

    logs: List[CapabilityLogEvent] = Field(
        default_factory=list,
        description="Structured log events from execution"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (tool, version, config, etc.)"
    )

    @model_validator(mode='after')
    def validate_status_invariants(self) -> 'CapabilityResult[T]':
        """
        Enforce invariants between status and other fields.

        This ensures orchestrators can rely on the structure:
        - Errors always have error objects and machine codes
        - Successes never have error objects
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

        return self

    # Convenience constructors

    @classmethod
    def ok(
            cls,
            data: T,
            msg: str = "Success",
            metadata: Optional[Dict[str, Any]] = None,
            logs: Optional[List[CapabilityLogEvent]] = None,
            duration_sec: float = 0.0
    ) -> "CapabilityResult[T]":
        """
        Create a successful result.

        Args:
            data: The result payload
            msg: Human-readable success message
            metadata: Optional metadata dict
            logs: Optional log events from execution
            duration_sec: Execution time in seconds

        Returns:
            CapabilityResult with status=success

        Example:
            >>> result = CapabilityResult.ok(
            ...     data={"clips": [...]},
            ...     msg="Generated 5 clips",
            ...     metadata={"tool": "slice_video", "preset": "fast"}
            ... )
        """
        return cls(
            status=CapabilityStatus.success,
            data=data,
            human_message=msg,
            metadata=metadata or {},
            logs=logs or [],
            duration_sec=duration_sec
        )

    @classmethod
    def skip(
            cls,
            reason: str,
            code: str = "QC_SKIPPED_POLICY",
            metadata: Optional[Dict[str, Any]] = None
    ) -> "CapabilityResult[T]":
        """
        Create a skip result (valid policy decision).

        Skips are NOT errors - they represent intentional decisions
        to skip processing (e.g., video too short, file already exists).

        Args:
            reason: Human-readable explanation for the skip
            code: Machine-readable skip code
            metadata: Optional metadata dict

        Returns:
            CapabilityResult with status=skipped

        Example:
            >>> result = CapabilityResult.skip(
            ...     reason="Video duration under 10 seconds",
            ...     code="QC_VAL_TOO_SHORT"
            ... )
        """
        return cls(
            status=CapabilityStatus.skipped,
            human_message=reason,
            machine_message=code,
            metadata=metadata or {}
        )

    @classmethod
    def fail(
            cls,
            msg: str,
            code: str,
            exception: Optional[Exception] = None,
            metadata: Optional[Dict[str, Any]] = None,
            logs: Optional[List[CapabilityLogEvent]] = None
    ) -> "CapabilityResult[T]":
        """
        Create an error result.

        Args:
            msg: Human-readable error message
            code: Machine-readable error code (QC_* format)
            exception: Optional exception that caused the error
            metadata: Optional metadata dict
            logs: Optional log events from execution

        Returns:
            CapabilityResult with status=error

        Example:
            >>> result = CapabilityResult.fail(
            ...     msg="Failed to read video file",
            ...     code="QC_IO_NOT_FOUND",
            ...     exception=FileNotFoundError("/data/video.mp4")
            ... )
        """
        err_details: Dict[str, Any] = {}
        if exception:
            err_details = {
                "type": type(exception).__name__,
                "str": str(exception),
            }

        return cls(
            status=CapabilityStatus.error,
            human_message=msg,
            machine_message=code,
            error=CapabilityError(code=code, message=msg, details=err_details),
            metadata=metadata or {},
            logs=logs or []
        )

    @classmethod
    def fail_from_exc(
            cls,
            msg: str,
            code: str,
            exc: Exception,
            metadata: Optional[Dict[str, Any]] = None
    ) -> "CapabilityResult[T]":
        """
        Convenience wrapper for fail() that always includes exception.

        Args:
            msg: Human-readable error message
            code: Machine-readable error code
            exc: Exception that caused the error
            metadata: Optional metadata dict

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
        return cls.fail(msg=msg, code=code, exception=exc, metadata=metadata)