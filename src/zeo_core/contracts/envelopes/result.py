"""
The canonical result envelope for all capabilities.

Consumed by: ALL Ring B tools, Ring C orchestrators (n8n, Temporal, runners)
Must NOT contain: Business logic, orchestration, side effects

This is the heart of the contracts system - every capability must return
a CapabilityResult to enable machine branching and audit trails.
"""

from datetime import datetime
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zeo_core.contracts.common.enums import CapabilityOutcome, CapabilityStatus
from zeo_core.contracts.common.ids import generate_run_id
from zeo_core.contracts.common.time import utcnow
from zeo_core.contracts.envelopes.error import CapabilityError
from zeo_core.contracts.envelopes.log import CapabilityLogEvent

T = TypeVar("T")

OUTCOME_TO_STATUS: dict[CapabilityOutcome, CapabilityStatus] = {
    CapabilityOutcome.success: CapabilityStatus.success,
    CapabilityOutcome.policy_skipped: CapabilityStatus.skipped,
    CapabilityOutcome.unavailable: CapabilityStatus.skipped,
    CapabilityOutcome.guard_rejected: CapabilityStatus.error,
    CapabilityOutcome.integration_failure: CapabilityStatus.error,
    CapabilityOutcome.invalid_return: CapabilityStatus.error,
    CapabilityOutcome.unexpected_exception: CapabilityStatus.error,
    CapabilityOutcome.cancelled: CapabilityStatus.error,
}


class CapabilityResult(BaseModel, Generic[T]):
    """
    Standard return envelope for ALL capabilities.

    Orchestrators (n8n, Temporal) parse this JSON to decide the next step
    in the workflow. This enables:
    - Machine branching (success/skip/error paths)
    - Audit trails (logs, timing, metadata)
    - Debugging (structured errors with context)

    Invariants:
        - If status == error, then error must be present AND machine_message
          must be present
        - If status == error, then machine_message must start with a
          recognized prefix (ZEO_ preferred; QC_/ZC_ accepted, see below)
        - If status == success, then error must be None AND machine_message
          should be None
        - If status == skipped, then error must be None AND machine_message
          must be present
        - If status == skipped, then machine_message must start with a
          recognized prefix (ZEO_ preferred; QC_/ZC_ accepted, see below)
        - If machine_message is present, it must start with a recognized
          prefix (ZEO_ preferred; QC_/ZC_ accepted, see below)

    Machine-message / error-code prefix:
        New code should use ``ZEO_<AREA>_<DETAIL>`` (matches the package
        name, zeo_core). ``QC_<AREA>_<DETAIL>`` is still accepted -- it is
        the convention this package's capabilities used before the
        pre-extraction rename from ``quack_core`` to ``zeo_core``, and it
        remains valid on purpose (not a leftover bug) because orchestrators
        already branch on `QC_*` codes emitted by existing tools; widening
        the validator to also accept `ZEO_`/`ZC_` was chosen over a hard
        rename so no existing call site or downstream consumer breaks.
        ``ZC_`` is accepted as a short-form alias of ``ZEO_``.

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
        ...     code="ZEO_VAL_TOO_SHORT"
        ... )

        >>> # Error
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     result = CapabilityResult.fail_from_exc(
        ...         msg="Failed to process video",
        ...         code="ZEO_IO_ERROR",
        ...         exc=e
        ...     )
    """

    model_config = ConfigDict(
        extra="forbid",  # Strict schema - no unexpected fields
    )

    # Core status
    status: CapabilityStatus = Field(
        ..., description="Execution status for machine branching"
    )

    outcome: CapabilityOutcome | None = Field(
        None,
        description=(
            "Fine-grained outcome. Defaults from status for legacy constructors: "
            "success→success, skipped→policy_skipped, error→integration_failure. "
            "The invoke helper always sets this explicitly."
        ),
    )

    # Payload (the actual value produced by the capability)
    data: T | None = Field(
        None, description="The actual result data (type varies by capability)"
    )

    # Telemetry
    run_id: str = Field(
        default_factory=generate_run_id,
        description=(
            "Unique identifier for this execution (should match RunManifest.run_id)"
        ),
    )

    timestamp: datetime = Field(
        default_factory=utcnow, description="UTC timestamp when result was created"
    )

    duration_sec: float | None = Field(
        None, ge=0.0, description="Execution duration in seconds (None if not measured)"
    )

    # Messages
    human_message: str = Field(..., description="Readable summary for logs/CLI/UI")

    machine_message: str | None = Field(
        None,
        description=(
            "Machine-readable code for orchestrator branching "
            "(must start with ZEO_, ZC_, or the legacy QC_)"
        ),
    )

    # Diagnostics
    error: CapabilityError | None = Field(
        None, description="Structured error info if status == error"
    )

    logs: list[CapabilityLogEvent] = Field(
        default_factory=list, description="Structured log events from execution"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (tool, version, config, etc.)",
    )

    #: Recognized machine-message / error-code prefixes. ZEO_ is the
    #: preferred, current convention (matches the zeo_core package name);
    #: QC_ is accepted for backward compatibility with call sites and
    #: orchestrators that predate the quack_core -> zeo_core rename; ZC_ is
    #: accepted as ZEO_'s short-form alias. See CapabilityResult's class
    #: docstring for the full rationale.
    MACHINE_MESSAGE_PREFIXES: ClassVar[tuple[str, ...]] = ("ZEO_", "ZC_", "QC_")

    @field_validator("machine_message")
    @classmethod
    def validate_machine_message_format(cls, v: str | None) -> str | None:
        """Ensure machine_message follows a recognized *_ convention when present."""
        if v is not None and not v.startswith(cls.MACHINE_MESSAGE_PREFIXES):
            raise ValueError(
                f"machine_message must start with one of "
                f"{cls.MACHINE_MESSAGE_PREFIXES}, got: {v}. "
                "Use format: ZEO_<AREA>_<DETAIL> (e.g., ZEO_VAL_TOO_SHORT)"
            )
        return v

    @model_validator(mode="after")
    def validate_status_invariants(self) -> "CapabilityResult[T]":
        """
        Enforce invariants between status and other fields.

        This ensures orchestrators can rely on the structure:
        - Errors always have error objects and machine codes
        - Successes never have error objects or machine codes
        - Skips never have error objects but always have machine codes
        """
        if self.status == CapabilityStatus.error:
            if self.error is None:
                raise ValueError("status=error requires error field to be present")
            if self.machine_message is None:
                raise ValueError("status=error requires machine_message for branching")

        if self.status == CapabilityStatus.success:
            if self.error is not None:
                raise ValueError("status=success must not have error field")
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

        self._coerce_outcome()
        return self

    def _coerce_outcome(self) -> None:
        if self.outcome is None:
            if self.status == CapabilityStatus.success:
                self.outcome = CapabilityOutcome.success
            elif self.status == CapabilityStatus.skipped:
                self.outcome = CapabilityOutcome.policy_skipped
            else:
                self.outcome = CapabilityOutcome.integration_failure
        elif OUTCOME_TO_STATUS[self.outcome] != self.status:
            raise ValueError(
                f"outcome {self.outcome} is incompatible with status {self.status}"
            )

    # Convenience constructors

    @classmethod
    def ok(
        cls,
        data: T,
        msg: str = "Success",
        metadata: dict[str, Any] | None = None,
        logs: list[CapabilityLogEvent] | None = None,
        duration_sec: float | None = None,
        run_id: str | None = None,
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
            "outcome": CapabilityOutcome.success,
            "data": data,
            "human_message": msg,
            "metadata": metadata or {},
            "logs": logs or [],
            "duration_sec": duration_sec,
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
        run_id: str | None = None,
    ) -> "CapabilityResult[T]":
        """
        Create a skip result (valid policy decision).

        Skips are NOT errors - they represent intentional decisions
        to skip processing (e.g., video too short, file already exists).

        Args:
            reason: Human-readable explanation for the skip
            code: Machine-readable skip code (must start with ZEO_, ZC_, or
                the legacy QC_ -- see MACHINE_MESSAGE_PREFIXES)
            metadata: Optional metadata dict
            run_id: Optional run_id to reuse (should match manifest run_id)

        Returns:
            CapabilityResult with status=skipped

        Example:
            >>> result = CapabilityResult.skip(
            ...     reason="Video duration under 10 seconds",
            ...     code="ZEO_VAL_TOO_SHORT"
            ... )
        """
        kwargs = {
            "status": CapabilityStatus.skipped,
            "outcome": CapabilityOutcome.policy_skipped,
            "human_message": reason,
            "machine_message": code,
            "metadata": metadata or {},
        }
        if run_id is not None:
            kwargs["run_id"] = run_id
        return cls(**kwargs)

    @classmethod
    def unavailable(
        cls,
        reason: str,
        code: str = "ZEO_CAP_UNAVAILABLE",
        metadata: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> "CapabilityResult[T]":
        """Create a skipped result because a declared dependency is missing."""
        kwargs: dict[str, Any] = {
            "status": CapabilityStatus.skipped,
            "outcome": CapabilityOutcome.unavailable,
            "human_message": reason,
            "machine_message": code,
            "metadata": metadata or {},
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
        run_id: str | None = None,
        outcome: CapabilityOutcome = CapabilityOutcome.integration_failure,
    ) -> "CapabilityResult[T]":
        """
        Create an error result.

        Args:
            msg: Human-readable error message
            code: Machine-readable error code (must start with ZEO_, ZC_, or
                the legacy QC_ -- see MACHINE_MESSAGE_PREFIXES)
            exception: Optional exception that caused the error
            metadata: Optional metadata dict
            logs: Optional log events from execution
            run_id: Optional run_id to reuse (should match manifest run_id)

        Returns:
            CapabilityResult with status=error

        Example:
            >>> result = CapabilityResult.fail(
            ...     msg="Failed to read video file",
            ...     code="ZEO_IO_NOT_FOUND",
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
            "outcome": outcome,
            "human_message": msg,
            "machine_message": code,
            "error": CapabilityError(code=code, message=msg, details=err_details),
            "metadata": metadata or {},
            "logs": logs or [],
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
        run_id: str | None = None,
    ) -> "CapabilityResult[T]":
        """
        Convenience wrapper for fail() that always includes exception.

        Args:
            msg: Human-readable error message
            code: Machine-readable error code (must start with ZEO_, ZC_, or
                the legacy QC_ -- see MACHINE_MESSAGE_PREFIXES)
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
            ...         code="ZEO_IO_ERROR",
            ...         exc=e
            ...     )
        """
        return cls.fail(
            msg=msg,
            code=code,
            exception=exc,
            metadata=metadata,
            run_id=run_id,
            outcome=CapabilityOutcome.unexpected_exception,
        )
