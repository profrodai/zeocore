"""
Connections domain contracts (Ring A / Kernel), ZC0-KERNEL-SEAM-01 step 1.

Frozen pure contracts for connectors, connections, effect authorization,
executions, normalized errors and receipts, plus the execution state
transition table. No adapter imports. No persistence. No secret material.

This package is step 1 of the seven-step binding order in
ZC0-KERNEL-SEAM-01: SecretStore/ConnectionStore/EffectAuthorizationVerifier
protocols (step 2), macOS Keychain custody (step 3), SQLite persistence
(step 4), connector admission and the fake provider adapter (step 5), and
orchestration (step 6) are deliberately NOT part of this package -- they
belong to `zeo_core.connections` (not yet built) and later leases of this
stream, per the packet's binding order: each step's proof surface depends
on the previous step landing first and not being reordered.
"""

from zeo_core.contracts.connections.authorization import EffectAuthorization
from zeo_core.contracts.connections.connection import Connection
from zeo_core.contracts.connections.connector import (
    BusinessOperation,
    ConnectorRevision,
)
from zeo_core.contracts.connections.enums import (
    ConnectionHealth,
    ConnectionStatus,
    ExecutionState,
    IdempotencyMode,
    NormalizedErrorCode,
    RiskClass,
)
from zeo_core.contracts.connections.errors import NormalizedError
from zeo_core.contracts.connections.execution import Execution
from zeo_core.contracts.connections.identity import (
    AuthorizationId,
    ConfirmationEvidenceRef,
    ConnectionId,
    ConnectorId,
    ConnectorRevisionId,
    ExecutionId,
    IdempotencyKey,
    OperationId,
    OrganizationId,
    SecretRef,
)
from zeo_core.contracts.connections.receipt import ExecutionReceipt
from zeo_core.contracts.connections.transitions import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    is_allowed_transition,
    is_terminal,
)

__all__ = [
    # Identity
    "OrganizationId",
    "ConnectorId",
    "ConnectorRevisionId",
    "ConnectionId",
    "OperationId",
    "AuthorizationId",
    "ExecutionId",
    "IdempotencyKey",
    "SecretRef",
    "ConfirmationEvidenceRef",
    # Enums
    "ExecutionState",
    "NormalizedErrorCode",
    "ConnectionStatus",
    "ConnectionHealth",
    "RiskClass",
    "IdempotencyMode",
    # Transition table
    "ALLOWED_TRANSITIONS",
    "TERMINAL_STATES",
    "is_allowed_transition",
    "is_terminal",
    # Domain models
    "BusinessOperation",
    "ConnectorRevision",
    "Connection",
    "EffectAuthorization",
    "Execution",
    "NormalizedError",
    "ExecutionReceipt",
]
