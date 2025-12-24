"""
The canonical interface for all QuackCore capabilities.
This module has ZERO dependencies on other QuackCore internal modules.
"""
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid

T = TypeVar("T")

class CapabilityStatus(str, Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    ERROR = "error"

class CapabilityLogEvent(BaseModel):
    """Structured log event for debugging/audit trails in n8n."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = "INFO"  # INFO, WARN, ERROR
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)

class CapabilityError(BaseModel):
    """Structured error info for machine handling."""
    code: str  # e.g., QC_VAL_FILE_MISSING
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

    # Telemetry & Observability
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_sec: float = 0.0
    
    # Messages
    human_message: str = Field(..., description="Readable summary for logs/CLI")
    machine_message: Optional[str] = Field(None, description="Error code or status code for n8n branching")
    
    # Diagnostics
    error: Optional[CapabilityError] = None
    logs: List[CapabilityLogEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T, msg: str = "Success", metadata: Dict[str, Any] = None) -> "CapabilityResult[T]":
        """Helper for successful execution."""
        return cls(
            status=CapabilityStatus.SUCCESS,
            data=data,
            human_message=msg,
            metadata=metadata or {}
        )

    @classmethod
    def skip(cls, reason: str, code: str = "QC_SKIPPED_POLICY") -> "CapabilityResult[T]":
        """Helper for valid skips (policy/logic decisions)."""
        return cls(
            status=CapabilityStatus.SKIPPED,
            human_message=reason,
            machine_message=code
        )

    @classmethod
    def fail(cls, msg: str, code: str, exception: Exception = None) -> "CapabilityResult[T]":
        """Helper for failures."""
        err_details = {"exception": str(exception)} if exception else {}
        return cls(
            status=CapabilityStatus.ERROR,
            human_message=msg,
            machine_message=code,
            error=CapabilityError(code=code, message=msg, details=err_details)
        )