"""
Structured error model for capability failures.

Consumed by: Ring B (tools), Ring C (orchestrators)
Must NOT contain: Error handling logic, retry logic
"""

from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator


class CapabilityError(BaseModel):
    """
    Structured error information for machine handling.

    Enables orchestrators (n8n, Temporal) to make intelligent routing
    decisions based on error codes without parsing error messages.

    Error Code Convention:
        - Format: ZEO_<AREA>_<DETAIL> (preferred, matches the zeo_core
          package name). QC_<AREA>_<DETAIL> is also accepted -- it predates
          this package's rename from quack_core and remains valid on
          purpose so existing orchestrator branching logic keeps working;
          ZC_<AREA>_<DETAIL> is accepted as ZEO_'s short-form alias.
        - Examples:
            - ZEO_CFG_ERROR: Configuration error
            - ZEO_IO_NOT_FOUND: File not found
            - ZEO_NET_TIMEOUT: Network timeout
            - ZEO_VAL_INVALID: Validation failure

    Example:
        >>> error = CapabilityError(
        ...     code="ZEO_IO_NOT_FOUND",
        ...     message="Video file not found at /data/video.mp4",
        ...     details={"path": "/data/video.mp4", "exists": False}
        ... )
    """

    code: str = Field(
        ...,
        description=(
            "Machine-readable error code (ZEO_*, ZC_*, or legacy QC_* format)"
        ),
        examples=["ZEO_CFG_ERROR", "ZEO_IO_NOT_FOUND", "ZEO_NET_TIMEOUT"],
    )

    message: str = Field(..., description="Human-readable error description")

    details: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Additional context for debugging (exception type, stack traces, etc.)"
        ),
    )

    #: Recognized error-code prefixes -- kept identical to
    #: CapabilityResult.MACHINE_MESSAGE_PREFIXES since machine_message and
    #: CapabilityError.code are the same convention used in two places.
    CODE_PREFIXES: ClassVar[tuple[str, ...]] = ("ZEO_", "ZC_", "QC_")

    @field_validator("code")
    @classmethod
    def validate_error_code_format(cls, v: str) -> str:
        """
        Enforce the ZEO_*/ZC_*/QC_* error code convention.

        Error codes must start with a recognized prefix for machine routing
        consistency. ZEO_ is preferred for new code; QC_ remains accepted
        for backward compatibility with call sites and orchestrators that
        predate the quack_core -> zeo_core rename. This is strictly
        enforced (rather than left as a lint suggestion) so all
        orchestrators can rely on the format for branching logic.
        """
        if not v.startswith(cls.CODE_PREFIXES):
            raise ValueError(
                f"Error code must start with one of {cls.CODE_PREFIXES}, "
                f"got: {v}. Use format: ZEO_<AREA>_<DETAIL> "
                "(e.g., ZEO_IO_NOT_FOUND)"
            )
        return v
