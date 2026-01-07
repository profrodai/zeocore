# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/envelopes/log.py
# module: quack_core.contracts.envelopes.log
# role: module
# neighbors: __init__.py, error.py, result.py
# exports: CapabilityLogEvent
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

"""
Structured log event model for audit trails.

Consumed by: Ring B (tools), Ring C (orchestrators), monitoring systems
Must NOT contain: Logging implementation, log shipping logic
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from quack_core.contracts.common.enums import LogLevel
from quack_core.contracts.common.time import utcnow


class CapabilityLogEvent(BaseModel):
    """
    Structured log event for debugging and audit trails.

    Used to provide rich context during capability execution without
    cluttering the main result payload. Orchestrators can aggregate
    these for monitoring and debugging.

    Context Convention:
        Recommended keys for structured context:
        - tool: Name of the tool emitting the log
        - tool_version: Version of the tool
        - run_kind: "local" | "cloud" | "test"
        - step: Current step within a multi-step capability
        - duration_ms: Time taken for this specific operation
        - resource_id: Related artifact/resource identifier

    Example:
        >>> log = CapabilityLogEvent(
        ...     level=LogLevel.INFO,
        ...     message="Processing video slice",
        ...     context={
        ...         "tool": "slice_video",
        ...         "step": "extract_clip_2",
        ...         "duration_ms": 1234,
        ...         "clip_index": 2
        ...     }
        ... )
    """

    timestamp: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when log was created"
    )

    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Severity level of the log event"
    )

    message: str = Field(
        ...,
        description="Human-readable log message"
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured context for debugging (tool, step, metrics, etc.)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "timestamp": "2025-01-15T10:30:00Z",
                    "level": "INFO",
                    "message": "Started video slicing",
                    "context": {
                        "tool": "slice_video",
                        "run_kind": "local",
                        "clip_count": 5
                    }
                },
                {
                    "timestamp": "2025-01-15T10:30:15Z",
                    "level": "ERROR",
                    "message": "Failed to encode clip",
                    "context": {
                        "tool": "slice_video",
                        "step": "encode_clip_3",
                        "error_type": "FFmpegError",
                        "clip_index": 3
                    }
                }
            ]
        }
    )
