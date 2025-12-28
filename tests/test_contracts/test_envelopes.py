# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_contracts/test_envelopes.py
# role: tests
# neighbors: __init__.py, test_artifacts.py, test_capabilities.py, test_dependency_boundaries.py
# exports: TestCapabilityError, TestCapabilityLogEvent, TestCapabilityResult
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
Tests for envelope models (CapabilityResult, CapabilityError, CapabilityLogEvent).

Validates invariants, convenience methods, and JSON serialization.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from quack_core.contracts import (
    CapabilityResult,
    CapabilityError,
    CapabilityLogEvent,
    CapabilityStatus,
    LogLevel,
)


class TestCapabilityError:
    """Tests for CapabilityError model."""

    def test_basic_error_creation(self):
        """Test creating a basic error."""
        error = CapabilityError(
            code="QC_IO_NOT_FOUND",
            message="File not found",
            details={"path": "/data/missing.mp4"}
        )

        assert error.code == "QC_IO_NOT_FOUND"
        assert error.message == "File not found"
        assert error.details["path"] == "/data/missing.mp4"

    def test_error_serialization(self):
        """Test error serialization to JSON."""
        error = CapabilityError(
            code="QC_NET_TIMEOUT",
            message="Network timeout",
            details={"timeout_sec": 30}
        )

        data = error.model_dump()
        assert data["code"] == "QC_NET_TIMEOUT"
        assert data["details"]["timeout_sec"] == 30


class TestCapabilityLogEvent:
    """Tests for CapabilityLogEvent model."""

    def test_basic_log_creation(self):
        """Test creating a basic log event."""
        log = CapabilityLogEvent(
            level=LogLevel.INFO,
            message="Processing started",
            context={"tool": "slice_video"}
        )

        assert log.level == LogLevel.INFO
        assert log.message == "Processing started"
        assert log.context["tool"] == "slice_video"
        assert isinstance(log.timestamp, datetime)

    def test_log_default_timestamp(self):
        """Test that timestamp defaults to UTC now."""
        log = CapabilityLogEvent(
            message="Test message"
        )

        # Check that timestamp is recent (within last second)
        now = datetime.now(timezone.utc)
        assert (now - log.timestamp).total_seconds() < 1.0


class TestCapabilityResult:
    """Tests for CapabilityResult envelope."""

    def test_ok_result(self):
        """Test successful result creation."""
        result = CapabilityResult.ok(
            data={"count": 5},
            msg="Processing complete",
            metadata={"tool": "test"}
        )

        assert result.status == CapabilityStatus.success
        assert result.data == {"count": 5}
        assert result.human_message == "Processing complete"
        assert result.metadata["tool"] == "test"
        assert result.error is None

    def test_skip_result(self):
        """Test skip result creation."""
        result = CapabilityResult.skip(
            reason="Video too short",
            code="QC_VAL_TOO_SHORT"
        )

        assert result.status == CapabilityStatus.skipped
        assert result.data is None
        assert result.human_message == "Video too short"
        assert result.machine_message == "QC_VAL_TOO_SHORT"

    def test_fail_result(self):
        """Test error result creation."""
        result = CapabilityResult.fail(
            msg="Processing failed",
            code="QC_IO_ERROR"
        )

        assert result.status == CapabilityStatus.error
        assert result.human_message == "Processing failed"
        assert result.machine_message == "QC_IO_ERROR"
        assert result.error is not None
        assert result.error.code == "QC_IO_ERROR"

    def test_fail_from_exception(self):
        """Test error result from exception."""
        exc = ValueError("Invalid input")
        result = CapabilityResult.fail_from_exc(
            msg="Validation failed",
            code="QC_VAL_ERROR",
            exc=exc
        )

        assert result.status == CapabilityStatus.error
        assert result.error is not None
        assert result.error.details["type"] == "ValueError"
        assert result.error.details["str"] == "Invalid input"

    def test_error_status_requires_error_field(self):
        """Test that error status requires error field."""
        with pytest.raises(ValidationError) as exc_info:
            CapabilityResult(
                status=CapabilityStatus.error,
                human_message="Something failed",
                machine_message="QC_ERROR"
                # Missing error field
            )

        assert "error field" in str(exc_info.value).lower()

    def test_error_status_requires_machine_message(self):
        """Test that error status requires machine_message."""
        with pytest.raises(ValidationError) as exc_info:
            CapabilityResult(
                status=CapabilityStatus.error,
                human_message="Something failed",
                error=CapabilityError(code="QC_ERROR", message="Error")
                # Missing machine_message
            )

        assert "machine_message" in str(exc_info.value).lower()

    def test_success_status_forbids_error_field(self):
        """Test that success status cannot have error field."""
        with pytest.raises(ValidationError) as exc_info:
            CapabilityResult(
                status=CapabilityStatus.success,
                human_message="Success",
                data={"result": "ok"},
                error=CapabilityError(code="QC_ERROR", message="Error")
            )

        assert "must not have error" in str(exc_info.value).lower()

    def test_result_with_logs(self):
        """Test result with log events."""
        logs = [
            CapabilityLogEvent(level=LogLevel.INFO, message="Started"),
            CapabilityLogEvent(level=LogLevel.INFO, message="Completed")
        ]

        result = CapabilityResult.ok(
            data={"status": "done"},
            msg="Success",
            logs=logs
        )

        assert len(result.logs) == 2
        assert result.logs[0].message == "Started"

    def test_result_serialization(self):
        """Test result serialization to JSON."""
        result = CapabilityResult.ok(
            data={"value": 42},
            msg="Success"
        )

        data = result.model_dump()
        assert data["status"] == "success"
        assert data["data"]["value"] == 42
        assert "run_id" in data
        assert "timestamp" in data