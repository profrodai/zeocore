# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/envelopes/error.py
# module: quack_core.contracts.envelopes.error
# role: module
# neighbors: __init__.py, log.py, result.py
# exports: CapabilityError
# git_branch: refactor/toolkitWorkflow
# git_commit: 0f9247b
# === QV-LLM:END ===

"""
Structured error model for capability failures.

Consumed by: Ring B (tools), Ring C (orchestrators)
Must NOT contain: Error handling logic, retry logic
"""

from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator


class CapabilityError(BaseModel):
    """
    Structured error information for machine handling.

    Enables orchestrators (n8n, Temporal) to make intelligent routing
    decisions based on error codes without parsing error messages.

    Error Code Convention:
        - Format: QC_<AREA>_<DETAIL>
        - Examples:
            - QC_CFG_ERROR: Configuration error
            - QC_IO_NOT_FOUND: File not found
            - QC_NET_TIMEOUT: Network timeout
            - QC_VAL_INVALID: Validation failure

    Example:
        >>> error = CapabilityError(
        ...     code="QC_IO_NOT_FOUND",
        ...     message="Video file not found at /data/video.mp4",
        ...     details={"path": "/data/video.mp4", "exists": False}
        ... )
    """

    code: str = Field(
        ...,
        description="Machine-readable error code (QC_* format)",
        examples=["QC_CFG_ERROR", "QC_IO_NOT_FOUND", "QC_NET_TIMEOUT"]
    )

    message: str = Field(
        ...,
        description="Human-readable error description"
    )

    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for debugging (exception type, stack traces, etc.)"
    )

    @field_validator("code")
    @classmethod
    def validate_error_code_format(cls, v: str) -> str:
        """
        Enforce QC_* error code convention.

        Error codes must start with 'QC_' for machine routing consistency.
        This is strictly enforced to ensure all orchestrators can rely on
        the format for branching logic.
        """
        if not v.startswith("QC_"):
            raise ValueError(
                f"Error code must start with 'QC_', got: {v}. "
                "Use format: QC_<AREA>_<DETAIL> (e.g., QC_IO_NOT_FOUND)"
            )
        return v