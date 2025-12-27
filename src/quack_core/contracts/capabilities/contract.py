# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capabilities/contract.py
# module: quack_core.contracts.capabilities.contract
# role: module
# neighbors: __init__.py, demo.py
# exports: CapabilityStatus, LogLevel, CapabilityLogEvent, CapabilityError, CapabilityResult
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
The canonical interface for all QuackCore capabilities.
This module has ZERO dependencies on other QuackCore internal modules.
"""
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
import uuid

T = TypeVar("T")

class CapabilityStatus(str, Enum):
    success = "success"
    skipped = "skipped"
    error = "error"

class LogLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"

class CapabilityLogEvent(BaseModel):
    """Structured log event for debugging/audit trails in n8n."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: LogLevel = LogLevel.INFO
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)

class CapabilityError(BaseModel):
    """Structured error info for machine handling."""
    code: str  # Must be QC_*
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

class CapabilityResult(BaseModel, Generic[T]):
    """
    The standard return envelope for ALL capabilities.
    n8n will parse this JSON to decide the next step.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core Status
    status: CapabilityStatus

    # Payload (The actual value produced)
    data: Optional[T] = None

    # Telemetry
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_sec: float = 0.0

    # Messages
    human_message: str = Field(..., description="Readable summary for logs/CLI")
    machine_message: Optional[str] = Field(None, description="QC_* Error code for n8n branching")

    # Diagnostics
    error: Optional[CapabilityError] = None
    logs: List[CapabilityLogEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T, msg: str = "Success", metadata: Dict[str, Any] = None) -> "CapabilityResult[T]":
        """Helper for successful execution."""
        return cls(
            status=CapabilityStatus.success,
            data=data,
            human_message=msg,
            metadata=metadata or {}
        )

    @classmethod
    def skip(cls, reason: str, code: str = "QC_SKIPPED_POLICY") -> "CapabilityResult[T]":
        """Helper for valid skips (policy/logic decisions)."""
        return cls(
            status=CapabilityStatus.skipped,
            human_message=reason,
            machine_message=code
        )

    @classmethod
    def fail(cls, msg: str, code: str, exception: Exception = None) -> "CapabilityResult[T]":
        """Helper for failures."""
        err_details = {}
        if exception:
            err_details = {
                "type": type(exception).__name__,
                "str": str(exception)
            }

        return cls(
            status=CapabilityStatus.error,
            human_message=msg,
            machine_message=code,
            error=CapabilityError(code=code, message=msg, details=err_details)
        )

    @classmethod
    def fail_from_exc(cls, msg: str, code: str, exc: Exception) -> "CapabilityResult[T]":
        """Helper to wrap exceptions quickly."""
        return cls.fail(msg=msg, code=code, exception=exc)