"""
Connections domain contracts (Ring A / Kernel), ZC0-KERNEL-SEAM-01 steps 1-2.

Frozen pure contracts for connectors, connections, effect authorization,
executions, normalized errors and receipts, plus the execution state
transition table (step 1); the SecretStore, ConnectionStore and
EffectAuthorizationVerifier protocols and their verdict/result value types
(step 2). No adapter imports. No persistence. No secret material. No
permissive default implementation.

macOS Keychain custody (step 3), SQLite persistence (step 4), connector
admission and the fake provider adapter (step 5), and orchestration
(step 6) are deliberately NOT part of this package -- they belong to
`zeo_core.connections` (not yet built) and later leases of this stream, per
the packet's binding order: each step's proof surface depends on the
previous step landing first and not being reordered.
"""

from zeo_core.contracts.connections.authorization import EffectAuthorization
from zeo_core.contracts.connections.connection import Connection
from zeo_core.contracts.connections.connector import (
    BusinessOperation,
    ConnectorRevision,
)
from zeo_core.contracts.connections.enums import (
    AuthorizationRefusalReason,
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
from zeo_core.contracts.connections.protocols import (
    ConnectionStore,
    EffectAuthorizationVerifier,
    SecretStore,
)
from zeo_core.contracts.connections.receipt import ExecutionReceipt
from zeo_core.contracts.connections.transitions import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    is_allowed_transition,
    is_terminal,
)
from zeo_core.contracts.connections.verdicts import (
    AuthorizationVerdict,
    SecretHealth,
    SecretResolution,
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
    "AuthorizationRefusalReason",
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
    # Step-2 verdict/result value types
    "AuthorizationVerdict",
    "SecretHealth",
    "SecretResolution",
    # Step-2 protocols
    "SecretStore",
    "ConnectionStore",
    "EffectAuthorizationVerifier",
]
