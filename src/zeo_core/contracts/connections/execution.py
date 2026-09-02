"""
Execution record, per packet sections 5.5 and 10.2-10.3, disposition 12-13.

Consumed by: receipt contracts in this package; the (not-yet-built)
orchestration and persistence layers (steps 4 and 6, out of this step's
scope).
Must NOT contain: provider dispatch logic, retry policy, or any field a
caller could use to assert its own organization, connection or origin --
every identity field here is populated from an EffectAuthorization or from
trusted runtime context, never from caller-supplied request JSON
(disposition 8, 11).

This model represents "persist before effect" (disposition 13): an
Execution is meant to exist, durably, before any provider network call is
made -- the fields here (authorization digest, normalized request digest,
connection, revision, operation, idempotency identity) are exactly the set
disposition 13 says must be committed first. Building that persistence and
the actual pre-dispatch write is step 4/6 work; this step only fixes the
shape of what gets written.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zeo_core.contracts.connections.enums import ExecutionState
from zeo_core.contracts.connections.identity import (
    AuthorizationId,
    ConnectionId,
    ConnectorRevisionId,
    ExecutionId,
    IdempotencyKey,
    OperationId,
    OrganizationId,
)
from zeo_core.contracts.connections.transitions import is_terminal


class Execution(BaseModel):
    """
    One durable execution of an admitted business operation.

    `state` is one ExecutionState (see enums.py); validity of a *transition*
    between two states is the transition table's job (transitions.py), not
    this model's -- a bare Execution has no "previous state" to compare
    against, so it can only assert internal consistency of a single
    snapshot: a terminal state must have `completed_at` set and a non-
    terminal one must not.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: ExecutionId
    organization_id: OrganizationId
    connection_id: ConnectionId
    connector_revision: ConnectorRevisionId
    operation_id: OperationId
    authorization_id: AuthorizationId
    idempotency_key: IdempotencyKey
    authorization_digest: str = Field(..., min_length=1)
    request_digest: str = Field(..., min_length=1)
    state: ExecutionState
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def _completed_at_matches_terminality(self) -> Execution:
        terminal = is_terminal(self.state)
        if terminal and self.completed_at is None:
            raise ValueError(
                f"execution in terminal state {self.state!s} must carry completed_at"
            )
        if not terminal and self.completed_at is not None:
            raise ValueError(
                f"execution in non-terminal state {self.state!s} must not "
                "carry completed_at"
            )
        return self

    @model_validator(mode="after")
    def _updated_at_not_before_created_at(self) -> Execution:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be before created_at")
        return self
