"""Typed request guards and guard results. Side-effect free by contract."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from zeo_core.contracts.common.enums import CapabilityOutcome


class GuardIssue(BaseModel):
    """Machine-readable field/path detail for a guard rejection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    message: str
    code: str | None = None


class GuardResult(BaseModel):
    """Outcome of a request guard. Must not request approval or I/O."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ok: bool
    code: str | None = None
    message: str | None = None
    issues: tuple[GuardIssue, ...] = ()

    @classmethod
    def accept(cls) -> GuardResult:
        return cls(ok=True)

    @classmethod
    def reject(
        cls,
        message: str,
        code: str = "ZEO_CAP_GUARD_REJECTED",
        issues: tuple[GuardIssue, ...] = (),
    ) -> GuardResult:
        return cls(ok=False, code=code, message=message, issues=issues)


@runtime_checkable
class RequestGuard(Protocol):
    """Pre-invocation check over a validated request model."""

    def check(self, request: BaseModel) -> GuardResult: ...


# Documented default outcome for guard rejection (mapped by the invoke helper).
GUARD_REJECTION_OUTCOME = CapabilityOutcome.guard_rejected
